.. _install:
.. currentmodule:: eodms_api_client

How to Install
==============

There are 3 main ways to install :code:`eodms-api-client`

1. If you're using conda, download from `conda-forge`_:

.. code-block::

    conda install -n <name-of-conda-env> eodms-api-client -c conda-forge

2. No access to conda or not a fan? It's also on `PyPI`_:

.. code-block::

    pip install eodms-api-client

3. If you like playing with potentially-unstable code, install the source from `github`_:

.. code-block::

    pip install https://github.com/m9brady/eodms-api-client/archive/main.zip

Configuring .netrc
------------------

In order to not be bugged to enter your username/password every time, you may wish to create an EODMS entry in ``.netrc`` file (``_netrc`` on Windows) for your userprofile

For Linux/Mac users:

.. code-block::

    echo "machine data.eodms-sgdot.nrcan-rncan.gc.ca login <username> password <password>" >> ~/.netrc
    # set permissions to user-readwrite-only
    chmod 600 ~/.netrc

For Windows users:

.. code-block::

    cd %USERPROFILE%
    type nul >> _netrc
    notepad _netrc
    # in notepad, paste the following and replace the chevroned text
    machine data.eodms-sgdot.nrcan-rncan.gc.ca login <username> password <password>
    # save and quit notepad

.. _PyPI: https://pypi.org/project/eodms-api-client/
.. _conda-forge: https://anaconda.org/conda-forge/eodms-api-client
.. _github: https://github.com/m9brady/eodms-api-client