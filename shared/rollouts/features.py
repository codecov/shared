# This file "defines" features which actually should live in the worker. It
# serves as a model for how this feature flag utility is recommended to be used
# in other repositories: with a central file in which all experiments are
# declared so that it's easier to see how much runtime variability there is in
# the way our service behaves. Unreproducible bug report from a customer? Check
# if there have been any recent feature changes that sound related.
#
# PARALLEL_UPLOAD_PROCESSING_BY_ORG = Feature(
#     "parllel_upload_processing", 0.2, overrides={"codecov's id": True}
# )
#
# LIST_REPOS_GENERATOR_BY_ORG = Feature(
#     "list_repos_generator", 0.5, overrides={"codecov's id": True)
# )
