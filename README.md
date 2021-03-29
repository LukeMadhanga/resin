# Resin

> On the fly image resizing


## Prerequisites

- Docker
- AWS CLI
- SAM CLI


##### To run and deploy:

```bash
sam init --runtime python3.7 --name resin
sam local start-api -p3003 --profile=luke --env-vars=testenv.json 
sam package --template-file template.yaml --profile=luke --output-template-file deploy.yaml --s3-bucket=madhanga
sam deploy --capabilities CAPABILITY_IAM --profile=luke --template-file deploy.yaml --stack-name ResinV0
```

##### To install new packages

```bash
docker run --rm -it -v "$PWD":/code lambci/lambda:build-python3.7 bash
cd /code
virtualenv env
source env/bin/activate
pip install ...
```

##### For local invocaion

```bash
sam local invoke Resin --no-event
```
