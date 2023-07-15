=====
Socon
=====

.. image:: https://img.shields.io/badge/python-3.9-blue.svg
    :target: https://github.com/socon-dev/socon

.. image:: https://github.com/socon-dev/socon/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/socon-dev/socon/actions?query=workflow%3APython%20testing

.. image:: https://codecov.io/gh/socon-dev/socon/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/socon-dev/socon
    :alt: Code coverage Status

.. image:: https://github.com/socon-dev/socon/actions/workflows/linters.yml/badge.svg
    :target: https://github.com/socon-dev/socon/actions?query=workflow%3APython%20linting

.. image:: https://readthedocs.org/projects/socon/badge/?version=latest
    :target: https://socon.readthedocs.io/en/latest/
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


Socon is a microservice architecture framework that helps you focussing on
deploying/chaining individual commands with cuctom services between your different
projects. Socon's create a generic Django like project structure. It's a structure
that contains all the element for you to get started.

Documentation
=============

The full documentation is in the "``docs``" directory on `GitHub`_ or online at
https://socon.readthedocs.io/en/latest/

If you are just getting started, We recommend that you read the documentation in this
order:

* Read ``docs/intro/install.txt`` for instructions on how to install Socon.

* Walk through each tutorial in numerical order: ``docs/intro/tutorials``

* Jump to the ``docs/how-to`` for specific problems and use-cases.

* Checkout the ``docs/ref`` for more details about API's and functionalities.

Check ``docs/README`` for instructions on building an HTML version of the docs.

Architecture
============

Below a representation of how the framework is structured with a simple example
such as managing mulitple databases with different projects.

.. image:: https://github.com/socon-dev/socon/raw/main/docs/img/architecture.png
    :align: center
    :alt: socon-architecture

The architecture show two different block. Socon, which is the framework and User
which is a structure created by socon using the builtin `initialize` CLI.



Contribution
============

Anyone can contribute to Socon's development. Checkout our documentation
on how to get involved: `https://socon.readthedocs.io/en/latest/internals/contributing.html`

License
=======

Copyright Stephane Capponi and others, 2023
Distributed under the terms of the BSD-3-Clause license, Socon is free and
open source software.

Socon also reused codes from third-party. You can find the licenses of these
third-party in the `licenses`_ folder. Each files that has been reused and
modified contains an SPDX section to specify the license used and the Copyright.
If you want more information about our license and why we reused code
from third-party, check the ``docs/intro/overview.txt``

.. _licenses: https://github.com/socon-dev/socon/tree/master/licenses
.. _GitHub: https://github.com/socon-dev/socon/
