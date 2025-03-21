import cc_rustyribs


def run_comparison_using_rust(base_report, head_report, diff):
    return cc_rustyribs.run_comparison(
        base_report.rust_report.get_report(),
        head_report.rust_report.get_report(),
        cc_rustyribs.rustify_diff(diff),
    )
