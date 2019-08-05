import json
import requests
import os
import base64
import boto3
import hashlib
import re
import urllib.parse

from io import BytesIO
from PIL import Image, ImageOps, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class Resin:

    def __init__(self, path):
        img, ext, mime_type = self.process_input_path(path)

        self.image = Image.open(img)
        self.ext = ext
        self.mime_type = self.calculate_mime_type(mime_type, ext)
        self.default_ext = 'png'

    @staticmethod
    def process_input_path(path):
        """
        Process the file path

        :type path: str
        :param path: The path to the image

        :rtype: tuple
        :return: A tuple in the form (binary, file extension, content type)
        """

        extension = re.sub('^([a-zA-Z0-9]+).*', '\\1', os.path.splitext(path)[1][1:])

        req = requests.get(path, stream=True)
        req.raw.decode_content = True

        return (
            req.raw,
            extension,
            req.headers['Content-Type'] if 'Content-Type' in req.headers else 'application/octet-stream'
        )

    @staticmethod
    def calculate_mime_type(mime_type, file_ext=None):
        """
        Calculate the mime type for an image

        :type mime_type: str
        :param mime_type: The mimetype, as saved

        :type file_ext: string|None
        :param file_ext: A file extension, e.g. jpg

        :rtype: str
        :return: The mime type
        """

        if mime_type != 'application/octet-stream':
            return mime_type

        if file_ext:
            file_ext = file_ext.lower()
        else:
            return mime_type

        if file_ext == 'jpg' or file_ext == 'jpeg':
            return 'image/jpeg'

        if file_ext == 'png':
            return 'image/png'

        if file_ext == 'gif':
            return 'image/gif'

        return mime_type

    def thumbnail(self, width, height, centering=(.5, .5)):
        """
        Create a thumbnail of an image

        :type width: int
        :param width: Width of the thumbnail

        :type height: int
        :param height: Height of the thumbnail

        :type centering: tuple|None
        :param centering: A tuple in the form (float X location [0-1], float Y location [0-1])
        """

        self.image = ImageOps.fit(self.image, (width, height), Image.BICUBIC, centering=centering)

    def get_as_bytes(self, format=None):
        """
        Get the current image as bytes

        :type format: string|None
        :param format: The output image format

        :rtype: binary
        :return: Image binary
        """

        if not format:
            format = self.ext if self.ext else self.default_ext

        if format.lower() == 'jpg':
            format = 'jpeg'

        temp = BytesIO()
        self.image.save(temp, format=format, quality=100)

        return temp.getvalue()

    def upload_to_s3(self, image_binary, bucket_name, path, **kwargs):
        """
        Upload file binary to S3

        :type image_binary: bytes
        :param image_binary: Binary representing an image

        :type bucket_name: str
        :param bucket_name: The name of the bucket to upload to. From os.environ['BUCKET_NAME']

        :type path: str
        :param path: Where to save the file in the destination bucket

        :type kwargs: dict
        :param kwargs:

        :return:
        """

        policy = 'public-read'

        if 'policy' in kwargs:
            policy = kwargs['policy']

        s3 = boto3.resource('s3')
        s3.Bucket(bucket_name).put_object(
            Key=path,
            Body=image_binary,
            ACL=policy,
            ContentType=self.mime_type,
            CacheControl=kwargs['cache_control']
        )


def validate_src(path, signature=None):
    """
    Validate the source of the image. If the URL contains a domain which is matched to the ENV variable KNOWN_DOMAINS,
        then the path is validated. If the URL is not in known domains, then a GET parameter sgn is required

    :type path: str
    :param path: The image path

    :type signature: str|None
    :param signature: hashlib.md5(urllib.parse.quote(img_url, safe='') + os.environ['SIGNATURE_KEY']).hexdigest()

    :exception: Exception
    """

    path_parts = path.split('/')

    key = 2 if re.match(r'^http(s)?:', path_parts[0]) else 0

    domain = path_parts[key]

    known_domains = os.environ['KNOWN_DOMAINS']

    if known_domains:
        for x in known_domains.split(','):
            if domain.find(x) > -1:
                return True

    url_encoded = urllib.parse.quote(path, safe='')
    hashed_path = hashlib.md5(url_encoded.encode('utf-8') + os.environ['SIGNATURE_KEY'].encode('utf-8')).hexdigest()

    if hashed_path != signature:
        raise Exception('Failed to validate source file')


def process_request(path, params):
    """
    Process the request

    :type params: str
    :param path: The URL path, in the form /s/<width>x<height>/<img_url>[?sgn=signature]. In SAM-CLI, this path will NOT
        be encoded, but in real env, this will be encoded

    :type path: dict
    :param params: A dict of GET parameters

    :rtype: dict
    :return: An object with data for which to instantiate Resin
    """

    path = urllib.parse.unquote(path)

    path_parts = path.split('/')

    wh = path_parts[0]

    if not wh or not re.match(r'^\d+x\d+$', wh):
        raise Exception('Missing width/height')

    wh_parts = wh.split('x')

    width = int(wh_parts[0])
    height = int(wh_parts[1])

    centering = [.5, .5]

    src = '/'.join(path_parts[1:])

    validate_src(src, params['sgn'] if 'sgn' in params else None)

    output = {
        'src': src,
        'width': width,
        'height': height,
        'bleed': 0.0,
        'crop_centering': tuple(centering),
        'output_path': 's/%s/%s' % (wh, urllib.parse.quote(src, safe=''))
    }

    return output


def err(http_code, msg):
    """
    Return an error response

    :type http_code: int
    :param http_code: A HTTP status code

    :type msg: str
    :param msg: The error message

    :rtype: dict
    :return: A response as required by Lambda
    """

    return {
        'statusCode': http_code,
        'headers': {
            'Content-type': 'application/json',
            'Cache-control': 'max-age=0'
        },
        'body': json.dumps({
            'error': msg
        })
    }


def lambda_handler(event, context):
    """
    As required by Lambda

    :type event: dict
    :param event:

    :type context: -
    :param context:
    """

    if not os.environ['SIGNATURE_KEY'] or (os.environ['UPLOAD_TO_S3'] == 1 and not os.environ['BUCKET_NAME']):
        return err(500, 'Missing required configuration key')

    if 'pathParameters' not in event or 'path' not in event['pathParameters'] or not event['pathParameters']['path']:
        return err(422, 'Malformed path')

    params = {}

    if 'queryStringParameters' in event and event['queryStringParameters']:
        params = event['queryStringParameters']

    try:
        req = process_request(event['pathParameters']['path'], params)
    except Exception as ex:
        return err(422, str(ex))

    im = Resin(req['src'])

    im.thumbnail(req['width'], req['height'], centering=req['crop_centering'])

    image_binary = im.get_as_bytes()

    cache_control = os.environ['CACHE_CONTROL']

    if int(os.environ['UPLOAD_TO_S3']) == 1:
        bucket_name = os.environ['BUCKET_NAME']
        policy = os.environ['DEFAULT_OBJECT_POLICY']

        im.upload_to_s3(image_binary, bucket_name, req['output_path'], policy=policy, cache_control=cache_control)

    return {
        'statusCode': 200,
        'isBase64Encoded': True,
        'body': base64.b64encode(image_binary).decode("utf-8"),
        'headers': {
            'Content-type': im.mime_type,
            'Cache-control': 'max-age=31536000'
        }
    }
