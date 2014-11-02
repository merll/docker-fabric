.. _cli_utils:

Miscellaneous utilities
=======================
Docker-Fabric supports deployments with a set of additional tools. Some components rely on the command line interface
(CLI) of Docker, that can be run through Fabric.

.. _cli:

Docker command line interface
-----------------------------
Some functionality has been implemented using the Docker CLI mainly for performance reasons. It has turned out in
earlier tests that the download speed of container and image data through the SSH tunnel was extremely slow. This may
be due to the tunnelling. The effect is further increased by the fact that the remote API currently does not compress
any downstream data (e.g. container and image transfers to a client), although it accepts gzip-compressed upstream.

Containers
^^^^^^^^^^
The two functions :func:`~dockerfabric.cli.copy_resource` and :func:`~dockerfabric.cli.copy_resources`, as the name may
suggest, extract files and directories from a container. They behave slightly different from one another however:
Whereas the former is more simple, the latter aims for flexibility.

For downloading some files and packaging them into a tarball (similar to what the ``copy`` function of the API would do)
:func:`~dockerfabric.cli.copy_resource` is more appropriate. Example::

    from dockerfabric import cli
    cli.copy_resource('app_container', '/var/log/app', 'app_logs.tar.gz')

This downloads all files from ``/var/log/app`` in the container ``app_container`` onto the host, packages them into
a compressed tarball, and downloads that to your client. Finally, it removes the downloaded source files from the host.

If the copied resource is a directory, contents of this directory are packaged into the top level of the archive. This
behavior can be changed (i.e. having the directory on the root level) by setting the optional keyword argument
``contents_only=False``.

The more advanced :func:`~dockerfabric.cli.copy_resources` is suitable for complex tasks. It does not create
a tarball and does not download to your client, but can copy multiple resources, and modify file ownership (`chown`) as
well as file permissions (`chmod`) after the download::

    ...
    resources = ['/var/lib/app/data1', '/var/lib/app/data2']
    temp_mapping = {'/var/lib/app/data1': 'd1', '/var/lib/app/data1': 'd2'}
    cli.copy_resources('app_container', resources, '/home/data', dst_directories=temp_mapping, apply_chmod='0750')

This example downloads two directories from ``app_container``, stores them in a folder ``/home/data``, and
changes the file system permissions to read-write for the owner, read-only for the group, and no access for anyone else.

The directories would by default be stored within their original structure, but in this example are renamed to ``d1``
and ``d2``. This is also possible with files. In order to override the generic fallback mapping (e.g. to something else
than the resource name), add a key ``*`` to the dictionary. That way contents of multiple directories can be merged into
one.

In case you would rather compress and download these files and directories, instead use
:func:`~dockerfabric.cli.isolate_and_get`. Similar to ``copy_resource`` contents are only stored temporarily and
downloaded as a single gzip-compressed tarball, but with the same options as :func:`~dockerfabric.cli.copy_resources`::

    cli.isolate_and_get('app_container', resources, 'container.tar.gz', dst_directories=temp_mapping)

It results in tar archive with ``d1`` and ``d2`` as top-level elements.

Since Docker also supports creating images from tar files, :func:`~dockerfabric.cli.isolate_to_image` can generate an
image that contains only the selected resources. Instead of a target file or directory, specify an image name instead::

    cli.isolate_to_image('app_container', resources, 'new_image', dst_directories=temp_mapping)

Note that the image at that point still has no configuration. In order for being able to run it as a container, some
executable file needs to be included.

Images
^^^^^^
As an alternative to the remote API ``save_image``, :func:`~dockerfabric.cli.save_image` stores the contents of an
entire image into a compressed tarball and downloads that. It takes two arguments, the image and the tarball::

    cli.save_image('app_image', 'app_image.tar.gz')

The function :func:`~dockerfabric.cli.flatten_image` works different from ``save_image``: It downloads the contents of
an image and stores them in a new one. This can reduce the size, but comes with a couple of limitations.

A template container has to be created from the image first, and started with a command that makes no further
modifications. For Linux images including the core utilities, such a command is typically ``/bin/true``; where
applicable it should be changed using the keyword argument ``no_op_cmd``::

    cli.flatten_image('app_image', 'new_image', no_op_cmd='/true')

If the second argument is not provided, the original image is overwritten. Like ``isolate_to_image``, the original
configuration is not transferred to the new image.

Fabric context managers
-----------------------
The following context managers complement :mod:`fabric.context_managers`. They are referenced in
other areas of Docker-Fabric, and can also be used directly for deployments.

.. note:: Docker-Fabric includes more utility functions. Not all are described here, but are documented with the
          package :mod:`dockerfabric.utils`.

For some purposes it may be useful to create a temporary container from an image, copy some data from it, and destroy it
afterwards. This is provided by :func:`~dockerfabric.utils.containers.temp_container`::

    with temp_container('app_image', no_op_cmd='/true'):
        ...

In fact it is not a requirement that the command provided in the keyword argument ``no_op_cmd`` actually performs no
changes. The command should finish without any interaction however, as the function waits before
processing further commands inside that block. Further supported arguments are ``create_kwargs`` and ``start_kwargs``,
for cases where it is necessary to modify the create and start options of a temporary container.

Management of local files, e.g. for copying around container contents, is supported with two more temporary contexts:
:func:`~dockerfabric.utils.files.temp_dir` creates a temporary directory on the remote host, that is removed after
leaving the context block. An alias should be assigned for use inside the context block::

    with temp_dir() as remote_tmp:
        cli.copy_resources('app_container', resources, remote_tmp, dst_directories=temp_mapping, apply_chmod='0750')
        ...
    ...
    # Directory is removed at this point

The local counterpart is :func:`~dockerfabric.utils.files.local_temp_dir`: It creates a temporary folder on the client
side::

    with local_temp_dir() as local_tmp:
        cli.copy_resource('app_container', '/var/log/app', os.path.join(local_tmp, 'app_logs.tar.gz'))
        ...
