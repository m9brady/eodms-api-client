.. _install
.. currentmodule:: eodms_api_client

How to Install
==============

Use the package listed on the Python Package Index (`PyPI`_):

.. code-block:: console

    pip install eodms-api-client

Install the latest version directly from github (potentially unstable):

.. code-block:: console

    pip install https://github.com/m9brady/eodms-api-client/archive/main.zip

Configuring .netrc
------------------

In order to not be bugged to enter your username/password every time, you may wish to create an EODMS entry in ``.netrc`` file (``_netrc`` on Windows) for your userprofile

For Linux/Mac users:

.. code-block:: console

    echo "machine data.eodms-sgdot.nrcan-rncan.gc.ca login <username> password <password>" >> ~/.netrc
    # set permissions to user-readwrite-only
    chmod 600 ~/.netrc

For Windows users:

.. code-block:: console

    cd %USERPROFILE%
    type nul >> _netrc
    notepad _netrc
    # in notepad, paste the following and replace the chevroned text
    machine data.eodms-sgdot.nrcan-rncan.gc.ca login <username> password <password>
    # save and quit notepad

.. _PyPI: https://pypi.org/project/eodms-api-client/