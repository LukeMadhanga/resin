# Resin

> On the fly image resizing


## Prerequisites

* Docker
* AWS CLI (`brew install awscli`)
* SAM CLI (`brew tap aws/tap && brew install aws-sam-cli && sam --version`)
* AWS credentials set in `~/.aws/credentials`
* Understanding of SAM ([watch here](https://www.youtube.com/watch?v=bih5b3C1nqc))

#### Running and Deployment

##### Local invocation

You may want to ensure that your local SAM setup is up and ready. To do so, run the following command. Note, 
it may take a while to download the docker image for SAM on the first run. 

```bash
sam local invoke Resin --no-event
# START RequestId: ... Version: $LATEST
# END RequestId: ...
# REPORT RequestId: ...	
# {"statusCode": 500, "headers": {"Content-type": "application/json", "Cache-control": "max-age=0"}, "body": "{\"error\": \"Missing required configuration key\"}"}
```

If you get errors, it may be to do with the Python version used by SAM


##### To run locally:


```bash
cp example-testenv.json testenv.json  # Needed the first time only
nano testenv.json  # Set the environment variables
sam local start-api [-p<port>] [--profile=<aws-profile>] --env-vars=testenv.json
# Mounting Resin at http://127.0.0.1:3030/s/{path+}
# ...
```

* You can set `-p<port>` to use a port other than the default `3000`.
* You can use `--profile=<aws-profile>` to use another profile that you have stored in `~/.aws/credentials`.

When running, we'll be able to navigate `localhost:<port>/s/<width>x<height>/<base_64>[/base_name[?sgn=signature]]` to 
invoke the script. In `example-testenv.json`, Flickr's CDN is whitelisted. If you keep this example, you can test the setup 
[this link](http://127.0.0.1:3030/s/300x300/aHR0cHM6Ly9saXZlLnN0YXRpY2ZsaWNrci5jb20vNDU1My8zODQ3MzYyMDMxNl9lZGY0MGVhYTI2X2suanBn). 
Note, this can be slow as SAM-CLI mounts the package into the runtime container.


#### Development

##### To install new packages in a fork

You need to install packages for Python3.7 as that's the environment that Lambda will use in production. To do so, you'll
need to install the package in a `virtalenv` in a docker image similar to Lambda's, and then copy the files from the 
`virtualenv` to your code repository.

```bash
docker run --rm -it -v "$PWD":/code lambci/lambda:build-python3.7 bash
cd /code
virtualenv env
source env/bin/activate
pip install [package-name]
cp env/lib/python3.7/site-packages/[package-name] resin/
```

#### Deployment

##### Deploying from local to AWS

```bash
sam package --template-file template.yaml [--profile=<aws-profile>] --output-template-file deploy.yaml --s3-bucket=<bucket-name>
sam deploy --capabilities CAPABILITY_IAM [--profile=<aws-profile>] --template-file deploy.yaml --stack-name ResinV0
```

##### Environment variables

| Name | Description |
| ---- | ----------- |
| BUCKET_NAME | If `UPLOAD_TO_S3` set to `1`, then the name of the bucket to upload to. |
| CACHE_CONTROL | Default `max-age=31536000` |
| DEFAULT_OBJECT_POLICY | Default `public-read` |
| KNOWN_DOMAINS | A comma separated list of domains. If the source image is from one of these domains, then the image can be processed, otherwise a "signature" is required |
| SIGNATURE_KEY | A string to provide basic protection when using images from domains outside `KNOWN_DOMAINS`. Equivalent to `md5(path + SIGNATURE_KEY)`, and appended to the URL with the parameter `?sgn=<value>` |

##### URL Structure

The URL in the template is written as `/s/{path+}`. If this path is not met, then you'll get the error

```
{"message":"Missing Authentication Token"}
```

A full URL example is

```
/s/<width>x<height>/<base64-src>/base-name.jpg?sgn=value
```

* `/s/` Required to create a sub-folder in your bucket to keep resized images separate.
* `<width>x<height>` e.g. `300x300`, the width and height of the image. Creates a sub-folder under `/s/`.
* `<base64-src>` This is the source of the image. If the image was not base64, then we'd break S3 (and our CloudFront fallback would fail).
    * This can be a base64 URL
    * Or a base64 JSON object with options (see below).
* `<basename>` [optional] The basename, for SEO.
* `?sgn` [optional] Use only if the image source is not from a "known domain".


URL JSON Options

| Key | default | Description |
| --- | ------- | ----------- |
| s | | Required. The source of the image |
| c | [0.5, 0.5] | Optional. In the event a crop is performed, the centering of the crop as a percentage between 0 and 1 |
| q | 80 | Optional. The quality of the scale between 0 and 100 |

##### CloudFront

This part is optional but recommended. It is implemented after you have successfully deployed your lambda application. 
As things stand, we will always resize images using our lambda script which is expensive. We will instead use 
CloudFront Origin Groups to only ever resize an image if it does not exist.

Example
* Navigate to `xxx.cloudfront.net/s/wxh/image-source/basename.png`.
* CloudFront hasn't cached the image.
* CloudFront requests the image from S3.
* S3 returns either 404 or 403.
* CloudFront fails over to Lambda.
* Lambda generates the image, saves it on S3 and then returns the binary.
* ... Time passes
* Navigate again to `xxx.cloudfront.net/s/wxh/image-source/basename.png`.
* Image is no longer in CloudFront's cache.
* CloudFront requests the image from S3.
* S3 returns the image.


To set up


1. Create a new [CloudFront distribution](https://console.aws.amazon.com/cloudfront/home) using the bucket you set for the environment variable `BUCKET_NAME`.
2. On the `Origins and Origin Groups` tab, click `Create Origin`.
3. Find the Lambda URL for your new app.
    - Set the base path as `Origin Domain Name`, e.g. `<id>.execute-api.eu-west-1.amazonaws.com`.
    - Set `/Prod` as `Origin Path`. (`/Prod` comes from `template.yaml: Outputs.ResinApi.Value`).
4. Save the new origin.
5. On the `Origins and Origin Groups` again, click `Create Origin Group`.
6. Set the S3 origin as the primary endpoint, and then add the Lambda origin as the backup.
7. Select `404` and `403` as the only `Failover criteria`.

#### Example Implementations

* Laravel
    - `cp implementations/laravel/ImageResize.php ~/laravel-project/app/Utilities/`
    - `cp implementations/laravel/ImageResizeTest.php ~/laravel-project/tests/Feature/`
    - `composer dump-autoload`
    - Copy the stub in `implementations/laravel/helpers.php` to your Laravel project's `helpers.php`
    - Copy the example env vars in `implementations/laravel/env` to your `.env` and `.env.example`.
    - `{!! imageResize('known-domain-image-source')->setDimensions(width, height)->render(['attribute' => 'value']) !!}`
    - `{!! imageResize('random-image-source')->setDimensions(width, height)->sign(true)->render(['class' => 'w-100']) !!}`
