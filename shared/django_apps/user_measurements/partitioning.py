from dateutil.relativedelta import relativedelta
from psqlextra.partitioning import (
    PostgresCurrentTimePartitioningStrategy,
    PostgresPartitioningManager,
    PostgresTimePartitionSize,
)
from psqlextra.partitioning.config import PostgresPartitioningConfig

from shared.django_apps.reports.models import DailyTestRollup
from shared.django_apps.user_measurements.models import UserMeasurement

# Overlapping partitions will cause errors - https://www.postgresql.org/docs/current/ddl-partitioning.html#DDL-PARTITIONING-DECLARATIVE -> "create partitions"
manager = PostgresPartitioningManager(
    [
        # 12 partitions ahead, each partition is 1 month
        # Partitions can be deleted after 12 months of their starting date, not their creation, via the pgpartition command.
        # They won't be automatically deleted though.
        # Partitions will be named `[table_name]_[year]_[3-letter month name]`.
        PostgresPartitioningConfig(
            model=UserMeasurement,
            strategy=PostgresCurrentTimePartitioningStrategy(
                size=PostgresTimePartitionSize(months=1),
                count=12,
                max_age=relativedelta(months=12),
            ),
        ),
        PostgresPartitioningConfig(
            model=DailyTestRollup,
            strategy=PostgresCurrentTimePartitioningStrategy(
                size=PostgresTimePartitionSize(months=1),
                count=3,
                max_age=relativedelta(months=3),
            ),
        ),
    ]
)
