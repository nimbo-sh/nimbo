# Nimbo: Run jobs on AWS with a single command
[Nimbo](https://nimbo.sh) is a CLI tool that allows you to run code on AWS as if you were running it locally. Nimbo also provides many useful commands to make it faster to work with AWS, such as easily checking prices, logging onto an instance, or syncing data.

Nimbo drastically simplifies your AWS workflow by taking care of instance, environment, data, and IAM management - no changes to your codebase needed. Since it is independent of your code, you can run any type of job you want

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
Please visit the [Getting started](https://nimbo.sh/getting-started) page in the docs.


## Examples
Sample projects can be found at our examples repo, [nimbo-examples](https://github.com/nimbo-sh/nimbo-examples).
Current examples include:
- [Finetuning an object segmentation network with Detectron2](https://github.com/nimbo-sh/nimbo-examples/tree/main/detectron)
- [Training a neural network on MNIST with Pytorch](https://github.com/nimbo-sh/nimbo-examples/tree/main/pytorch-mnist)
- [Training a neural network on MNIST with Tensorflow, on a spot instance](https://github.com/nimbo-sh/nimbo-examples/tree/main/tensorflow-mnist)

## Developing
If you want to make changes to the codebase, you can clone this repo and use `pip install -e .` to install nimbo locally. As you make code changes, your local
nimbo installation will automatically update

### Running Tests
In order to run the tests you have to change the `aws_profile`, `security_group`, and `instance_key` parameters in the `tests/assets/nimbo-config.yml` file to your own values.
After that, you can use `pytest` to run the tests:
```bash
pytest -x
```
