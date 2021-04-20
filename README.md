
<p align="center">
  <img src="https://user-images.githubusercontent.com/6595222/115258675-1bf98300-a129-11eb-8ea1-24cdc67d81e8.png" width="480" height="240">
</p>

# Nimbo: Run jobs on AWS with a single command

[Nimbo](https://nimbo.sh) is a CLI tool that allows you to run code on AWS as if you were running it locally. It's as simple as:

### nimbo run "python train.py --lr=3e-4"

It also provides many useful commands to make it faster to work with AWS, such as easily checking prices, logging onto an instance, or syncing data. For example:
- nimbo list-spot-gpu-prices
- nimbo ssh <instance-id>
- nimbo push datasets
- nimbo pull logs
- nimbo delete-all-instances

Nimbo drastically simplifies your AWS workflow by taking care of instance, environment, data, and IAM management - no changes to your codebase needed. Since it is independent of your code, you can run any type of job you want.

## Key Features
- **Your Infrastructure:**
Code runs on your EC2 instances and data is stored in your S3 buckets. This means that you can easily use the resulting models and data from anywhere within your AWS organization, and use your existing permissions and credentials.
- **User Experience:**
Nimbo gives you the command line tools to make working with AWS as easy as working with local resources. No more complicated SDKs and never-ending documentation.
- **Customizable:**
Want to use a custom AMI? Just change the image ID in the Nimbo config file. Want to use a specific conda package? Just add it to your environment file. Nimbo is built with customization in mind, so you can use any setup you want.
- **Seamless Spot Instances**
With Nimbo, using spot instances is as simples as changing a single value on the config file. Enjoy the 70-90% savings with AWS spot instances with no changes to your workflow.
- **Managed Images**
We provide managed AMIs with the latest drivers, with unified naming across all regions. We will also release AMIs that come preloaded with ImageNet and other large datasets, so that you can simply spin up an instance and start training.

You can find more information at [nimbo.sh](https://nimbo.sh), or read the docs at [docs.nimbo.sh](https://docs.nimbo.sh).

## Getting started
Visit https://docs.nimbo.sh/getting-started to get started.

## Examples
Sample projects can be found at our examples repo, [nimbo-examples](https://github.com/nimbo-sh/nimbo-examples).
Current examples include:
- [Finetuning an object segmentation network with Detectron2](https://github.com/nimbo-sh/nimbo-examples/tree/main/detectron)
- [Training a neural network on MNIST with Pytorch](https://github.com/nimbo-sh/nimbo-examples/tree/main/pytorch-mnist)
- [Training a neural network on MNIST with Tensorflow, on a spot instance](https://github.com/nimbo-sh/nimbo-examples/tree/main/tensorflow-mnist)

## Product roadmap
- **Implement `nimbo notebook`:** You will be able to spin up a jupyter lab notebook running on an EC2 instance. Data will be continuously synced with your S3 bucket so that you don't have to worry about doing manual backups. Your local code will be automatically synced with the instance, so you can code locally and test the changes directly on the remote notebook. The notebook will also be synced with your local machine so you don't have to worry about losing your notebook changes when deleting the instance.
- **Add Docker support:** Right now we assume you are using a conda environment, but many people use docker to run jobs. This feature would allow you to run a command such as `nimbo run "docker-compose up"`, where the docker image would be fetched from DockerHub (or equivalent repository) through a `docker_image` parameter on the `nimbo-config.yml` file.
- **Add AMIs with preloaded large datasets:** Downloading and storing large datasets like ImageNet is a time consuming process. We will make available AMIs that come with an extra EBS volume mounted on `/datasets`, so that you can use large datasets without worrying about storing them or waiting for them to be fetched from your S3 bucket. Get in touch if you have datasets you would like to see preloaded with the instances. 
- **GCP support:** Use the same commands to run jobs on AWS or GCP. 


## Developing
If you want to make changes to the codebase, you can clone this repo and use `pip install -e .` to install nimbo locally. As you make code changes, your local
nimbo installation will automatically update

### Running Tests
In order to run the tests you have to change the `aws_profile`, `security_group`, and `instance_key` parameters in the `tests/assets/nimbo-config.yml` file to your own values.
After that, you can use `pytest` to run the tests:
```bash
pytest -x
```
