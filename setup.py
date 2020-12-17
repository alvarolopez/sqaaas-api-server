# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "sqaaas_api_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion==2.6.0",
    "swagger-ui-bundle==0.0.6",
    "aiohttp_jinja2==1.2.0",
    "PyGithub>=1.53",
    "python-jenkins>=1.7.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="SQAaaS API",
    author_email="orviz@ifca.unican.es",
    url="",
    keywords=["OpenAPI", "SQAaaS API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'openapi_server': [
        'LICENSE',
        'openapi/openapi.yaml',
        'templates/Jenkinsfile',
        '../etc/sqaaas.ini.sample']},
    include_package_data=False,
    entry_points={
        'console_scripts': ['sqaaas_api_server=openapi_server.__main__:main']},
    long_description="""\
    API for the Software and Service Quality Assurance as a Service (SQAaaS) component.
    """
)

