import json

from pulumi import Output
from pulumi import export
from pulumi import Config
from pulumi import runtime

from pulumi_docker import Image

from pulumi_gcp import storage

from pulumi_gcp.storage import get_transfer_project_service_account
from pulumi_gcp.storage import BucketIAMMember

from pulumi_gcp.artifactregistry import Repository
from pulumi_gcp.artifactregistry import RepositoryIamMember

from pulumi_gcp.serviceaccount import Account

from pulumi_gcp.compute import Instance

from pulumi_gcp.secretmanager import SecretVersion

from pulumi_gcp.projects import IAMMember

from pulumi_aws.iam import User
from pulumi_aws.iam import AccessKey
from pulumi_aws.iam import Policy
from pulumi_aws.iam import UserPolicyAttachment

from pulumi_aws.secretsmanager import Secret
from pulumi_aws.secretsmanager import SecretVersion as AwsSecretVersion


storage_transfer_service_account = get_transfer_project_service_account()


bucket = storage.Bucket(
    'test-pulumi-bucket',
    location='us-west1',
    force_destroy=True,
    soft_delete_policy={
        'retention_duration_seconds': 0,
    }
)


gc_project = Config('gcp').require('project')


member = BucketIAMMember(
    'member',
    bucket=bucket.name,
    role='roles/storage.objectViewer',
    member=f'serviceAccount:{storage_transfer_service_account.email}',
)


docker_registry = Repository(
    'test-repo-pulumi',
    location='us-west1',
    repository_id='some-repo',
    format='DOCKER'
)


repo_url = Output.concat(
    docker_registry.location,
    '-docker.pkg.dev/',
    gc_project,
    '/',
    docker_registry.repository_id,
)


image = Image(
    "custom-python",
    build={
        'context': './docker/python/',
        'dockerfile':'./docker/python/Dockerfile',
        'platform': 'linux/amd64',
    },
    image_name=repo_url.apply(lambda url: f'{url}/custom-python312:v0.0.7'),
    registry={
        'server': repo_url.apply(lambda url: f'{url}'),
    },
)


compute_service_account = Account(
    'compute-sa',
)


compute_storage_admin = BucketIAMMember(
    'compute-storage-admin',
    bucket=bucket.name,
    role='roles/storage.admin',
    member=Output.concat("serviceAccount:", compute_service_account.email),
)


storage_transfer_admin_binding = IAMMember(
    "compute-sa-storage-transfer-admin",
    project=gc_project,
    role="roles/storagetransfer.admin",
    member=compute_service_account.email.apply(lambda email: f'serviceAccount:{email}')
)


image_pull_permission = RepositoryIamMember(
    'image-pull-permission',
    repository=docker_registry.id,
    location=docker_registry.location,
    role="roles/artifactregistry.reader",
    member=Output.concat("serviceAccount:", compute_service_account.email),
)


test_secret = SecretVersion.get(
    resource_name='test-secret',
    id='projects/99884963860/secrets/test-secret/versions/1',
)


aws_user = User(
    'aws-user',
    name='test-pulumi-user',
)


aws_access_key = AccessKey(
    'aws-access-key',
    user=aws_user.name,
)


aws_secret = Secret(
    'aws-secret',
    name='test-pulumi-user-access-keys',
)


aws_secret_version = AwsSecretVersion(
    'aws-secret-version',
    secret_id=aws_secret.id,
    secret_string=Output.all(
        aws_access_key.id,
        aws_access_key.secret
    ).apply(lambda args: f'{{"ACCESS_KEY":"{args[0]}","SECRET_ACCESS_KEY":"{args[1]}"}}')
)


aws_bucket_name = 'hic-files-transfer'


aws_s3_read_policy = Policy(
    'aws-s3-read-policy',
    policy=Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{aws_bucket_name}",
                        f"arn:aws:s3:::{aws_bucket_name}/*"
                    ]
                }
            ]
        }
    )
)


aws_user_policy_attachment = UserPolicyAttachment(
    'aws-user-policy-attachment',
    user=aws_user.name,
    policy_arn=aws_s3_read_policy.arn
)


container_def = Output.all(
    image=image.base_image_name,
    secret_value=test_secret.secret_data,
    aws_secret_value=aws_secret_version.secret_string,
).apply(
    lambda args: json.dumps({
        "spec": {
            "containers": [
                {
                    "name": "test-container-1",
                    "image": args['image'],
                    "env": [
                        {"name": "ATHING", "value": "fromdef"},
                        {"name": "IMAGENAME", "value": args['image']},
                        {"name": "a", "value": json.loads(args['secret_value'])['a']},
                        {"name": "b", "value": json.loads(args['secret_value'])['secret']},
                        {"name": "AWS_ACCESS_KEY_ID", "value": json.loads(args['aws_secret_value'])['ACCESS_KEY']},
                        {"name": "AWS_SECRET_ACCESS_KEY", "value": json.loads(args['aws_secret_value'])['SECRET_ACCESS_KEY']},
                    ],
                    "stdin": True,
                    "tty": True
                }
            ],
            "restartPolicy": "Always"
        }
    })
)


compute_instance = Instance(
    resource_name='test-vm-with-container',
    boot_disk={
        'initialize_params': {
            'image': 'projects/cos-cloud/global/images/cos-stable-117-18613-164-98',
            'size': 32,
        }
    },
    machine_type='n2-standard-2',
    zone='us-west1-a',
    network_interfaces=[
        {
            'network': 'default',
            'access_configs': [{}]
        }
    ],
    metadata={
        'gce-container-declaration': container_def
    },
    service_account={
        'email': compute_service_account.email,
        'scopes': ['cloud-platform'],
    },
    allow_stopping_for_update=True,
)



export('bucket_name', bucket.url)
export('storage_transfer_service_account_email', storage_transfer_service_account.email)
export('storage_transfer_service_account_subject_id', storage_transfer_service_account.subject_id)
export('docker_registry_id', docker_registry.id)
export("imageName", image.base_image_name)
export('compute_service_account_email', compute_service_account.email)
export('aws_user_name', aws_user.name)
export('aws_user_name', aws_user.arn)
export('aws_access_key_id', aws_access_key.id)
export('aws_secret_arn', aws_secret.arn)
