## Implementation notes on prototype/1.1

SQAaaS API server's prototype 1.1 aims at covering the full set of features offered by JePL-2.1.0, and thus, it extends the MVP (released early 2021) to cover:
- Support for multi-stage `Jenkinsfile` by implementing the Jenkins' `when` property for [`branch`, `buildingTag`].
- Support for pushing Docker images: current only if the `build` property is defined (since JePL is using `docker-compose push`).
- Support for the (current) full set of build tools, both `tox` and `commands`.
- Support for modifying existing pipelines through the implementation of the `PUT /pipeline/<pipeline_id>` path.
- Extended validation (on top of the OpenAPI's models) of incoming request data, performed when creating or updating a pipeline. The current extended check is the validation of Docker push requests, i.e when composer's `push: true`, this check ensures that the correct credentials (`JPL_USERNAME`, `JPL_PASSNAME`) have been supplied.
- Temporary use of Docker Compose (DC)'s `working_dir` property: this is a workaround (will be supported by means of a new composer in JePL) so by default the working directory is the same as the volume's `target`. Note that this workaround fetches this value from the first volume it is defined, so it is actually _just doable with single-volume DC definitions_. The rationale behind this implementation is to avoid the requirement (to be done by the end user) to chdir in the given repository when using the build tool.
