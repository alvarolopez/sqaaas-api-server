# coding: utf-8

import pytest
import json
from aiohttp import web

from openapi_server.models.inline_object import InlineObject
from openapi_server.models.inline_response200 import InlineResponse200
from openapi_server.models.inline_response2001 import InlineResponse2001
from openapi_server.models.inline_response2002 import InlineResponse2002
from openapi_server.models.inline_response201 import InlineResponse201
from openapi_server.models.je_pl_composer import JePLComposer
from openapi_server.models.je_pl_config import JePLConfig
from openapi_server.models.je_pl_jenkinsfile import JePLJenkinsfile
from openapi_server.models.pipeline import Pipeline
from openapi_server.models.upstream_error import UpstreamError


async def test_add_pipeline(client):
    """Test case for add_pipeline

    Creates a pipeline.
    """
    body = {
  "config_data" : [ {
    "environment" : {
      "JPL_IGNOREFAILURES" : "defined",
      "JPL_DOCKERPUSH" : "docs service1 service4"
    },
    "sqa_criteria" : {
      "qc_style" : {
        "repos" : {
          "simple-java-maven-app" : {
            "container" : "checkstyle",
            "commands" : [ "mvn checkstyle:check" ]
          }
        }
      }
    },
    "config" : {
      "project_repos" : {
        "simple-java-maven-app" : {
          "repo" : "https://github.com/jenkins-docs/simple-java-maven-app",
          "branch" : "master"
        }
      },
      "credentials" : [ {
        "password_var" : "GIT_PASS",
        "username_var" : "GIT_USER",
        "id" : "my-dockerhub-token",
        "type" : "username_password"
      }, {
        "password_var" : "GIT_PASS",
        "username_var" : "GIT_USER",
        "id" : "my-dockerhub-token",
        "type" : "username_password"
      } ]
    },
    "timeout" : 0
  }, {
    "environment" : {
      "JPL_IGNOREFAILURES" : "defined",
      "JPL_DOCKERPUSH" : "docs service1 service4"
    },
    "sqa_criteria" : {
      "qc_style" : {
        "repos" : {
          "simple-java-maven-app" : {
            "container" : "checkstyle",
            "commands" : [ "mvn checkstyle:check" ]
          }
        }
      }
    },
    "config" : {
      "project_repos" : {
        "simple-java-maven-app" : {
          "repo" : "https://github.com/jenkins-docs/simple-java-maven-app",
          "branch" : "master"
        }
      },
      "credentials" : [ {
        "password_var" : "GIT_PASS",
        "username_var" : "GIT_USER",
        "id" : "my-dockerhub-token",
        "type" : "username_password"
      }, {
        "password_var" : "GIT_PASS",
        "username_var" : "GIT_USER",
        "id" : "my-dockerhub-token",
        "type" : "username_password"
      } ]
    },
    "timeout" : 0
  } ],
  "composer_data" : {
    "services" : {
      "checkstyle" : {
        "image" : {
          "name" : "checkstyle/maven-builder-image",
          "registry" : {
            "push" : true,
            "url" : "https://hub.docker.com/",
            "credential_id" : "my-dockerhub-cred"
          }
        },
        "hostname" : "checkstyle-host",
        "volumes" : [ {
          "source" : "./",
          "target" : "./simple-java-app",
          "type" : "bind"
        } ],
        "command" : "sleep 600000"
      }
    },
    "version" : "3.7"
  },
  "name" : "sqaaas-api-spec",
  "id" : "dd7d8481-81a3-407f-95f0-a2f1cb382a4b",
  "jenkinsfile_data" : {
    "stages" : [ {
      "pipeline_config" : {
        "credentials_id" : "userpass_dockerhub",
        "base_branch" : "https://github.com/jenkins-docs/simple-java-maven-app",
        "base_repository" : "master",
        "jepl_validator_docker_image" : "eoscsynergy/jpl-validator:1.1.0",
        "config_file" : "./.sqa/config.yml"
      },
      "when" : {
        "branches" : [ "master", "master" ]
      }
    }, {
      "pipeline_config" : {
        "credentials_id" : "userpass_dockerhub",
        "base_branch" : "https://github.com/jenkins-docs/simple-java-maven-app",
        "base_repository" : "master",
        "jepl_validator_docker_image" : "eoscsynergy/jpl-validator:1.1.0",
        "config_file" : "./.sqa/config.yml"
      },
      "when" : {
        "branches" : [ "master", "master" ]
      }
    } ]
  }
}
    headers = { 
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    response = await client.request(
        method='POST',
        path='/v1/pipeline',
        headers=headers,
        json=body,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_create_pull_request(client):
    """Test case for create_pull_request

    Creates pull request with JePL files.
    """
    body = openapi_server.InlineObject()
    headers = { 
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    response = await client.request(
        method='POST',
        path='/v1/pipeline/{pipeline_id}/pull_request'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        json=body,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_delete_pipeline_by_id(client):
    """Test case for delete_pipeline_by_id

    Delete pipeline by ID
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='DELETE',
        path='/v1/pipeline/{pipeline_id}'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_compressed_files(client):
    """Test case for get_compressed_files

    Get JePL files in compressed format.
    """
    headers = { 
        'Accept': 'application/zip',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}/compressed_files'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipeline_by_id(client):
    """Test case for get_pipeline_by_id

    Find pipeline by ID
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipeline_composer(client):
    """Test case for get_pipeline_composer

    Gets composer configuration used by the pipeline.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}/composer'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipeline_config(client):
    """Test case for get_pipeline_config

    Gets pipeline's main configuration.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}/config'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipeline_jenkinsfile(client):
    """Test case for get_pipeline_jenkinsfile

    Gets Jenkins pipeline definition used by the pipeline.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}/jenkinsfile'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipeline_status(client):
    """Test case for get_pipeline_status

    Get pipeline status.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline/{pipeline_id}/status'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_get_pipelines(client):
    """Test case for get_pipelines

    Gets pipeline IDs.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='GET',
        path='/v1/pipeline',
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')


async def test_run_pipeline(client):
    """Test case for run_pipeline

    Runs pipeline.
    """
    headers = { 
        'Accept': 'application/json',
    }
    response = await client.request(
        method='POST',
        path='/v1/pipeline/{pipeline_id}/run'.format(pipeline_id='pipeline_id_example'),
        headers=headers,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')

