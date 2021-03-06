"""Handle restoring items to airtable databases."""
import base64
import lzma
import hashlib
from uuid import uuid4

import airtable
import boto3
# import fs
# from fs_s3fs import S3FS
from airtable_local_backup import exceptions
from airtable_local_backup import common


def decode_file(item, check_integrity=True):
    """
    Decodes filedata store in backup dumps.

    Arguments:
        item: the file data to decode
        check_integrity: bool- flag whether to check the resulting data against
        the stored hash.

    Returns: dict: {'filename': name of the file, 'data': (bytes)decoded data}
    This data could be used as:
        with open(return['filename'], 'wb') as outfile:
            outfile.write(return['data']

    Raises DataCorruptionError if integrity check fails.
    """
    filedata = base64.b64decode(item['data'])
    if item['compressed']:
        body = lzma.decompress(filedata)
    else:
        body = filedata
    if check_integrity:
        bodyhash = hashlib.md5(body).hexdigest()
        if not bodyhash == item['md5hash']:
            raise exceptions.DataCorruptionError(
                'file: {} failed the data integrity check, '
                'and may be corrupted.')
    return {'filename': item['filename'], 'data': body.decode('utf-8')}


def prepare_records(table_data, *, s3fs=None, check_integrity=True,
                    prefix=''):
    """
    Reads table data from input stream and yields records for insertion into
    airtable.

    Arguments:
        table_data: a json object generated by DownloadTable
        s3fs: an fs_s3fs.S3FS object for uploading files and generating urls
            see s3fs documentation for usage with s3 or s3 compatible
            services.
        check_integrity: bool whether to run hash to check
        data integrity
        prefix: a prefix to add to objects. include a / for folders.
    Yields: a generator of json objects for uploading to airtable with s3
    endpoints for attachments if specified.
    """
    for record in table_data:
        newdata = {}
        # print(record)
        for key, value in record.items():
            if list(common._findkeys(value, 'filename')):
                urls = []
                if not s3fs:
                    continue
                for item in value:
                    filedata = decode_file(
                        item, check_integrity)
                    path = '{p}{u}'.format(p=prefix, u=uuid4())
                    with s3fs.open(path, 'w') as upfile:
                        upfile.write(filedata['data'])
                    url = s3fs.geturl(path)
                    urls.append({'url': url, 'filename': filedata['filename']})
                newdata[key] = urls
            else:
                newdata[key] = value
        yield newdata
