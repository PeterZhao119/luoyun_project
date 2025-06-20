#!/usr/bin/python
'''
Licensed to the Apache Software Foundation(ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at
http: // www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations under
the License.
'''
import os
import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

requires = [
    "oss2",
    "aliyun-python-sdk-core>=2.13.3",
    "matplotlib>=3.3.4"
]

setup_args = {
    'version': "1.1.0",
    'author': "jiaqi.sjq",
    'author_email': "jiaqi.sjq@alibaba-inc.com",
    'description': "python sdk for nls",
    'license':"Apache License 2.0",
    'long_description': long_description,
    'long_description_content_type': "text/markdown",
    'keywords': ["nls", "sdk"],
    'url': "https://github.com/..",
    'packages': ["nls", "nls/websocket"],
    'install_requires': requires,
    'classifiers': [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
}

setuptools.setup(name='nls', **setup_args)
