/*
These are the SQL queries used in Metabase so that we can make the feature flag experiment dashboards like this:
https://metabase.codecov.dev/question/170-experiment-dashboard-by-owner-id?variant_name=list_repos_generator&metric=worker.task.app.tasks.sync_repos.SyncRepos.core_runtime&start_date=2024-04-30

These SQL queries are used for the following two dashboards:
https://metabase.codecov.dev/question/175-experiment-dashboard-by-repo-id?variant_name=&metric=&start_date=
https://metabase.codecov.dev/question/170-experiment-dashboard-by-owner-id?variant_name=&metric=&start_date=

The code that gets executed on Metabase lives within Metabase, but ideally changes should be also checked-in to this file so that we have a version history.

The relevant tables are: `feature_exposures`, `telemetry_simple`, `feature_flags`, and `feature_flag_variants`. We bucket the timestamps based on the hour which is how we're able to correlate
feature exposures with the telemetry simple metrics. 

The {{___}} notation with {{variant_name}} or {{metric}} are a metabase specific thing that allow us to have variable dropdowns in the dashboard, which is configured through the Metabase UI. Note:
the values populated for {{metric}} are actually hardcoded because querying for all the metrics on-demand was too long of a query. If new metrics/celery tasks are added, those values need to be 
populated via the Metabase UI. 
*/

-- OWNER_ID DASHBOARD
SELECT
  "feature_flag_variants__via__feature_flag_variant_id"."name" AS "feature_flag_variants__via__feature_flag_variant_id__name",
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") AS "timestamp",
  COUNT(*) AS "samples",
  AVG("Telemetry Simple - Feature Flag"."value") AS "task runtime"
FROM
  "public"."feature_exposures"
 
LEFT JOIN "public"."telemetry_simple" AS "Telemetry Simple - Feature Flag" ON (
    DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") = DATE_TRUNC(
      'hour',
      "Telemetry Simple - Feature Flag"."timestamp"
    )
  )
 
   AND (
    "public"."feature_exposures"."owner" = "Telemetry Simple - Feature Flag"."owner_id"
  )
  LEFT JOIN "public"."feature_flag_variants" AS "feature_flag_variants__via__feature_flag_variant_id" ON "public"."feature_exposures"."feature_flag_variant_id" = "feature_flag_variants__via__feature_flag_variant_id"."variant_id"
WHERE
  (
    "public"."feature_exposures"."feature_flag_id" = {{variant_name}}
  )
  AND (
    "Telemetry Simple - Feature Flag"."name" = {{metric}}
  ) AND (
    "feature_exposures"."timestamp" > {{start_date}}
  )
GROUP BY
  "feature_flag_variants__via__feature_flag_variant_id"."name",
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp")
ORDER BY
  "feature_flag_variants__via__feature_flag_variant_id"."name" ASC,
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") ASC


-- REPO_ID DASHBOARD
SELECT
  "feature_flag_variants__via__feature_flag_variant_id"."name" AS "feature_flag_variants__via__feature_flag_variant_id__name",
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") AS "timestamp",
  COUNT(*) AS "samples",
  AVG("Telemetry Simple - Feature Flag"."value") AS "task runtime"
FROM
  "public"."feature_exposures"
 
LEFT JOIN "public"."telemetry_simple" AS "Telemetry Simple - Feature Flag" ON (
    DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") = DATE_TRUNC(
      'hour',
      "Telemetry Simple - Feature Flag"."timestamp"
    )
  )
 
   AND (
    "public"."feature_exposures"."repo" = "Telemetry Simple - Feature Flag"."repo_id"
  )
  LEFT JOIN "public"."feature_flag_variants" AS "feature_flag_variants__via__feature_flag_variant_id" ON "public"."feature_exposures"."feature_flag_variant_id" = "feature_flag_variants__via__feature_flag_variant_id"."variant_id"
WHERE
  (
    "public"."feature_exposures"."feature_flag_id" = {{variant_name}}
  )
  AND (
    "Telemetry Simple - Feature Flag"."name" = {{metric}}
  ) AND (
    "feature_exposures"."timestamp" > {{start_date}}
  )
GROUP BY
  "feature_flag_variants__via__feature_flag_variant_id"."name",
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp")
ORDER BY
  "feature_flag_variants__via__feature_flag_variant_id"."name" ASC,
  DATE_TRUNC('hour', "public"."feature_exposures"."timestamp") ASC