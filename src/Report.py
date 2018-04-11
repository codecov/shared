from copy import copy
from json import dumps
from itertools import chain
from src.ReportFile import ReportFile
from src.utils.ReportEncoder import ReportEncoder
from src.utils.merge import *
from src.utils.make_network_file import make_network_file
from src.utils.tuples import *
from src.helpers.Yaml import Yaml
from src.utils.agg_totals import agg_totals
from src.utils.sum_totals import sum_totals
from src.helpers.zfill import zfill
from src.helpers.flag import Flag
from src.utils.sessions import Session
from src.utils.flare import report_to_flare
from src.utils.migrate import migrate_totals
from src.utils.match import match, match_any

END_OF_CHUNK = '\n<<<<< end_of_chunk >>>>>\n'


class Report(object):
    file_class = ReportFile

    def __init__(self, files=None, sessions=None,
                 totals=None, chunks=None, diff_totals=None,
                 yaml=None, flags=None, **kwargs):
        # {"filename": [<line index in chunks :int>, <ReportTotals>]}
        self._files = files or {}

        # {1: {...}}
        self.sessions = dict((sid, Session(**session))
                             for sid, session
                             in sessions.iteritems()) if sessions else {}

        # ["<json>", ...]
        if isinstance(chunks, basestring):
            # came from archive
            chunks = chunks.split(END_OF_CHUNK)
        self._chunks = chunks or []

        # <ReportTotals>
        if isinstance(totals, ReportTotals):
            self._totals = totals

        elif totals:
            self._totals = ReportTotals(*migrate_totals(totals))

        else:
            self._totals = None

        self._path_filter = None
        self._line_modifier = None
        self._filter_cache = (None, None)
        self.diff_totals = diff_totals
        self.yaml = yaml  # ignored

    @property
    def network(self):
        if self._path_filter:
            for fname, data in self._files.iteritems():
                file = self.get(fname)
                if file:
                    yield fname, make_network_file(
                        file.totals
                    )
        else:
            for fname, data in self._files.iteritems():
                yield fname, make_network_file(*data[1:])

    def __repr__(self):
        try:
            return '<%s files=%s>' % (
                self.__class__.__name__,
                len(getattr(self, '_files', [])))
        except:
            return '<%s files=n/a>' % self.__class__.__name__

    @property
    def files(self):
        """returns a list of files in the report
        """
        path_filter = self._path_filter
        if path_filter:
            # return filtered list of filenames
            return [filename
                    for filename, _ in self._files.iteritems()
                    if self._path_filter(filename)]
        else:
            # return the fill list of filenames
            return self._files.keys()

    @property
    def flags(self):
        """returns dict(:name=<Flag>)
        """
        return {flag: Flag(self, flag)
                for flag
                in set(chain(*((session.flags or [])
                               for sid, session
                               in self.sessions.iteritems())))}

    def append(self, _file, joined=True):
        """adds or merged a file into the report
        """
        if _file is None:
            # skip empty adds
            return False

        elif not isinstance(_file, ReportFile):
            raise TypeError('expecting ReportFile got %s' % type(_file))

        elif len(_file) == 0:
            # dont append empty files
            return False

        assert _file.name, 'file must have a name'

        session_n = len(self.sessions) - 1

        # check if file already exists
        index = self._files.get(_file.name)
        if index:
            # existing file
            # =============
            # add session totals
            if len(index) < 3:
                # [TEMP] this may be temporary, as old report dont have sessoin totals yet
                index.append([])
            index[2].append(copy(_file.totals))
            #  merge old report chunk
            cur_file = self[_file.name]
            # merge it
            cur_file.merge(_file, joined)
            # set totals
            index[1] = cur_file.totals
            # update chunk in report
            self._chunks[index[0]] = cur_file
        else:
            # new file
            # ========
            session_totals = ([None] * session_n) + [_file.totals]

            # override totals
            if not joined:
                _file._totals = ReportTotals(0, _file.totals.lines)

            # add to network
            self._files[_file.name] = [
                len(self._chunks),       # chunk location
                _file.totals,            # Totals
                session_totals,          # Session Totals
                None                     # Diff Totals
            ]

            # add file in chunks
            self._chunks.append(_file)

        self._totals = None

        return True

    def get(self, filename, _else=None, bind=False):
        """
        returns <ReportFile>
        if not found return _else

        :bind will replace the chunks and bind file changes to the report
        """
        if self._path_filter and not self._path_filter(filename):
            # filtered out of report
            return _else

        _file = self._files.get(filename)
        if _file is not None:
            if self._chunks:
                try:
                    lines = self._chunks[_file[0]]
                except:
                    lines = None
                    print '[DEBUG] file not found in chunk', _file[0]
            else:
                # may be tree_only request
                lines = None
            if isinstance(lines, ReportFile):
                lines.apply_line_modifier(self._line_modifier)
                return lines
            report_file = self.file_class(name=filename,
                                          totals=_file[1],
                                          lines=lines,
                                          line_modifier=self._line_modifier)
            if bind:
                self._chunks[_file[0]] = report_file

            return report_file

        return _else

    def ignore_lines(self, ignore_lines):
        """
        :ignore_lines {"path": {"lines": ["1"]}}
        only used during processing and does not effect the chunks inside this Report object
        """
        for path, data in ignore_lines.iteritems():
            _file = self.get(path)
            if _file is not None:
                _file.ignore_lines(**data)

    def resolve_paths(self, paths):
        """
        :paths [(old_path, new_path), ...]
        """
        already_added_to_file = []
        for old_path, new_path in paths:
            if old_path in self:
                if new_path in already_added_to_file:
                    del self[old_path]
                elif new_path is None:
                    del self[old_path]
                else:
                    already_added_to_file.append(new_path)
                    if old_path != new_path:
                        # rename and ignore lines
                        self.rename(old_path, new_path)

    def rename(self, old, new):
        # remvoe from list
        _file = self._files.pop(old)
        # add back with new name
        self._files[new] = _file
        # update name if it was a ReportFile
        chunk = self._chunks[_file[0]]
        if isinstance(chunk, ReportFile):
            chunk.name = new
        return True

    def __getitem__(self, filename):
        _file = self.get(filename)
        if _file is None:
            raise IndexError('File at path %s not found in report' % filename)
        return _file

    def __delitem__(self, filename):
        # remove from report
        _file = self._files.pop(filename)
        # remove chunks
        self._chunks[_file[0]] = None
        return True

    def get_folder_totals(self, path):
        """
        returns <ReportTotals> for files contained in a folder
        """
        path = path.strip('/') + '/'
        return sum_totals((self[filename].totals
                           for filename, _ in self._files.iteritems()
                           if filename.startswith(path)))

    @property
    def totals(self):
        if not self._totals:
            # reprocess totals
            self._totals = self._process_totals()
        return self._totals

    def _process_totals(self):
        """Runs through the file network to aggregate totals
        returns <ReportTotals>
        """
        _path_filter = self._path_filter or bool
        _line_modifier = self._line_modifier

        def _iter_totals():
            for filename, data in self._files.iteritems():
                if not _path_filter(filename):
                    continue
                elif _line_modifier or data[1] is None:
                    # need to rebuild the file because there are line filters
                    yield self.get(filename).totals
                else:
                    yield data[1]

        totals = agg_totals(_iter_totals())
        if self._filter_cache and self._filter_cache[1]:
            flags = set(self._filter_cache[1])
            totals[9] = len([1
                             for _, session in self.sessions.iteritems()
                             if set(session.flags or []) & flags])
        else:
            totals[9] = len(self.sessions)

        return ReportTotals(*tuple(totals))

    @property
    def manifest(self):
        """returns a list of files in the report
        """
        if self._path_filter:
            return filter(self._path_filter, self._files.keys())

        else:
            return self._files.keys()

    def add_session(self, session):
        sessionid = len(self.sessions)
        self.sessions[sessionid] = session
        if self._totals:
            # add session to totals
            self._totals = self._totals._replace(sessions=sessionid+1)
        return sessionid, session

    def __iter__(self):
        """Iter through all the files
        yielding <ReportFile>
        """
        for filename, _file in self._files.iteritems():
            if self._path_filter and not self._path_filter(filename):
                # filtered out
                continue
            if self._chunks:
                report = self._chunks[_file[0]]
            else:
                report = None
            if isinstance(report, ReportFile):
                yield report
            else:
                yield self.file_class(name=filename,
                                      totals=_file[1],
                                      session_totals=_file[2] if len(_file) > 2 else None,
                                      lines=report,
                                      line_modifier=self._line_modifier)

    def __contains__(self, filename):
        return filename in self._files

    def merge(self, new_report, joined=True):
        """combine report data from another
        """
        if new_report is None:
            return

        elif not isinstance(new_report, Report):
            raise TypeError('expecting type Report got %s' % type(new_report))

        elif new_report.is_empty():
            return

        # merge files
        for _file in new_report:
            if _file.name:
                self.append(_file, joined)

        self._totals = self._process_totals()

    def is_empty(self):
        """returns boolean if the report has no content
        """
        if self._path_filter:
            return len(filter(self._path_filter, self._files.keys())) == 0
        else:
            return len(self._files) == 0

    def __nonzero__(self):
        return self.is_empty() is False

    def to_archive(self):
        return END_OF_CHUNK.join(map(_encode_chunk, self._chunks)).encode("utf-8")

    def to_database(self):
        """returns (totals, report) to be stored in database
        """
        totals = dict(zip(TOTALS_MAP, self.totals))
        totals['diff'] = self.diff_totals
        return (totals,
                dumps({'files': self._files,
                       'sessions': self.sessions},
                      cls=ReportEncoder))

    def update_sessions(self, **data):
        pass

    def flare(self, changes=None, color=None):
        if changes is not None:
            """
            if changes are provided we produce a new network
            only pass totals if they change
            """
            # <dict path: totals if not new else None>
            changed_coverages = dict(
                ((_Change[0], _Change[5][5] if not _Change[1] and _Change[5] else None)
                 for _Change in changes)
            )
            # <dict path: stripeed if not in_diff>
            classes = dict(((_Change[0], 's') for _Change in changes if not _Change[3]))

            def _network():
                for name, _NetworkFile in self.network:
                    changed_coverage = changed_coverages.get(name)
                    if changed_coverage:
                        # changed file
                        yield name, ReportTotals(lines=_NetworkFile[0][1],
                                                 coverage=float(changed_coverage))
                    else:
                        diff = _NetworkFile.diff_totals
                        if diff and diff[1] > 0:  # lines > 0
                            # diff file
                            yield name, ReportTotals(lines=_NetworkFile[0][1],
                                                     coverage=-1 if float(diff[5]) < float(_NetworkFile[0][5]) else 1)

                        else:
                            # unchanged file
                            yield name, ReportTotals(lines=_NetworkFile[0][1])

            network = _network()

            def color(cov):
                return 'purple' if cov is None else \
                    '#e1e1e1' if cov == 0 else \
                        'green' if cov > 0 else \
                            'red'

        else:
            network = ((path, _NetworkFile[0])
                       for path, _NetworkFile
                       in self.network)
            classes = {}
            # [TODO] [v4.4.0] remove yaml from args, use below
            # color = self.yaml.get(('coverage', 'range'))

        return report_to_flare(network, color, classes)

    def reset(self):
        # remove my totals
        self._totals = None
        self._path_filter = None
        self._line_modifier = None
        self._filter_cache = None

    def filter(self, paths=None, flags=None):
        """Usage: with report.filter(repository, paths, flags) as report: ...
        """
        if self._filter_cache == (paths or None, flags or None):
            # same same
            return self

        self._filter_cache = (paths, flags)
        self.reset()

        if paths or flags:
            # reset all totals
            if paths:
                if not isinstance(paths, (list, set, tuple)):
                    raise TypeError('expecting list for argument paths got %s' % type(paths))

                def _pf(filename):
                    return match(paths, filename)

                self._path_filter = _pf

            # flags: filter them out
            if flags:
                if not isinstance(flags, (list, set, tuple)):
                    flags = [flags]

                # get all session ids that have this falg
                sessions = set([int(sid)
                                for sid, session
                                in self.sessions.iteritems()
                                if match_any(flags, session.flags)])

                # the line has data from this session
                def adjust_line(line):
                    new_sessions = [LineSession(*s)
                                    for s in (line.sessions or [])
                                    if int(s[0]) in sessions]
                    # check if line is applicable
                    if not new_sessions:
                        return False
                    return ReportLine(coverage=get_coverage_from_sessions(new_sessions),
                                      complexity=get_complexity_from_sessions(new_sessions),
                                      type=line.type,
                                      sessions=new_sessions,
                                      messages=line.messages)

                self._line_modifier = adjust_line

        return self

    def __enter__(self):
        """see self.filter
        Usage: with report.filter() as report: ...
        """
        return self

    def __exit__(self, *args):
        """remove filtering
        """
        # removes all filters
        self.reset()

    def does_diff_adjust_tracked_lines(self, diff, future_report, future_diff):
        """
        Returns <boolean> if the diff touches tracked lines

        master . A . C
        pull          \ . . B

        :diff = <diff> A...C
        :future_report = <report> B
        :future_diff = <diff> C...B

        future_report is necessary because it is used to determin if
        lines added in the diff are tracked by codecov
        """
        if diff and diff.get('files'):
            for path, data in diff['files'].iteritems():
                future_state = Yaml.walk(future_diff, ('files', path, 'type'))
                if (
                        data['type'] == 'deleted' and  # deleted
                        path in self                   # and tracked
                ):
                    # found a file that was tracked and deleted
                    return True

                elif (
                        data['type'] == 'new' and      # newly tracked
                        future_state != 'deleted' and  # not deleted in future
                        path in future_report          # found in future
                ):
                    # newly tracked file
                    return True

                elif data['type'] == 'modified':
                    in_past = path in self
                    in_future = future_state != 'deleted' and path in future_report
                    if in_past and in_future:

                        # get the future version
                        future_file = future_report.get(path, bind=False)
                        # if modified
                        if future_state == 'modified':
                            # shift the lines to "guess" what C was
                            future_file.shift_lines_by_diff(future_diff['files'][path],
                                                            forward=False)

                        if self.get(path).does_diff_adjust_tracked_lines(data, future_file):
                            # lines changed
                            return True

                    elif in_past and not in_future:
                        # missing in future
                        return True

                    elif not in_past and in_future:
                        # missing in pats
                        return True

        return False

    def shift_lines_by_diff(self, diff, forward=True):
        """
        [volitile] will permanently adjust repot report

        Takes a <diff> and offsets the line based on additions and removals
        """
        if diff and diff.get('files'):
            for path, data in diff['files'].iteritems():
                if (
                        data['type'] == 'modified' and
                        path in self
                ):
                    _file = self.get(path)
                    _file.shift_lines_by_diff(data, forward=forward)
                    chunk_loc = self._files[path][0]
                    # update chunks with file updates
                    self._chunks[chunk_loc] = _file
                    # clear out totals
                    self._files[path] = [chunk_loc, None, None, None]

    def apply_diff(self, diff, _save=True):
        """
        Add coverage details to the diff at ['coverage'] = <ReportTotals>
        returns <ReportTotals>
        """
        if diff and diff.get('files'):
            totals = []
            for path, data in diff['files'].iteritems():
                if data['type'] in ('modified', 'new'):
                    _file = self.get(path)
                    if _file:
                        fg = _file.get
                        lines = []
                        le = lines.extend
                        # add all new lines data to a new file to get totals
                        [le([fg(i)
                             for i, line in enumerate(filter(lambda l: l[0] != '-',
                                                             segment['lines']),
                                                      start=int(segment['header'][2]) or 1)
                             if line[0] == '+'])
                         for segment in data['segments']]

                        file_totals = ReportFile(name=None, totals=None, lines=lines).totals
                        totals.append(file_totals)
                        if _save:
                            data['totals'] = file_totals
                            # store in network
                            network_file = self._files[path]
                            if file_totals.lines == 0:
                                # no lines touched
                                file_totals = file_totals._replace(coverage=None,
                                                                   complexity=None,
                                                                   complexity_total=None)
                            self._files[path] = zfill(network_file, 3, file_totals)

            totals = sum_totals(totals)

            if totals.lines == 0:
                totals = totals._replace(coverage=None,
                                         complexity=None,
                                         complexity_total=None)

            if _save and totals.files:
                diff['totals'] = totals
                self.diff_totals = totals

            return totals

    def has_flag(self, flag_name):
        """
        Returns boolean: if the flag is found
        """
        for sid, data in self.sessions.iteritems():
            if flag_name in (data.flags or []):
                return True
        return False

    def assume_flags(self, flags, prev_report, name=None):
        with prev_report.filter(flags=flags) as filtered:
            # add the "assumed session"
            self.add_session(Session(
                flags=flags,
                totals=filtered.totals,
                name=name or 'Assumed'
            ))
            # merge the results
            self.merge(filtered)


def _encode_chunk(chunk):
    if chunk is None:
        return 'null'
    elif isinstance(chunk, ReportFile):
        return chunk._encode()
    elif isinstance(chunk, (list, dict)):
        return dumps(chunk, separators=(',', ':'))
    else:
        return chunk
