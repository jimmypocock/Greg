import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as appscaling from 'aws-cdk-lib/aws-applicationautoscaling';
import { Construct } from 'constructs';
import { EnvironmentConfig, ServiceConfig } from '../config';

export interface ServicesStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  ecsSecurityGroup: ec2.ISecurityGroup;
  ecsTaskExecutionRole: iam.IRole;
  ecsTaskRole: iam.IRole;
  cluster: ecs.ICluster;
  apiTargetGroup: elbv2.IApplicationTargetGroup;
  webTargetGroup: elbv2.IApplicationTargetGroup;
  apiRepository: ecr.IRepository;
  webRepository: ecr.IRepository;
  apiLogGroup: logs.ILogGroup;
  webLogGroup: logs.ILogGroup;
  workerLogGroup: logs.ILogGroup;
  databaseSecretArn: string;
  connectionStringsSecretArn: string;
  uploadsBucketName: string;
}

/**
 * Services Stack - API, Web, and Worker ECS Services
 *
 * This stack contains all services that can be deployed together.
 * For independent deployments, split into separate stacks.
 */
export class ServicesStack extends cdk.Stack {
  public readonly apiService: ecs.FargateService;
  public readonly webService: ecs.FargateService;
  public readonly workerService: ecs.FargateService;

  constructor(scope: Construct, id: string, props: ServicesStackProps) {
    super(scope, id, props);

    const { config } = props;
    const prefix = `songwriter-${config.environment}`;

    // =========================================================================
    // Secrets References
    // =========================================================================
    const connectionStringsSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this, 'ConnectionStrings', props.connectionStringsSecretArn
    );

    // JWT Secret - must be created manually
    const jwtSecretArn = `arn:aws:secretsmanager:${this.region}:${this.account}:secret:songwriter/${config.environment}/jwt`;

    // Optional secrets - check if they exist
    const stripeSecretArn = `arn:aws:secretsmanager:${this.region}:${this.account}:secret:songwriter/${config.environment}/stripe`;
    const openaiSecretArn = `arn:aws:secretsmanager:${this.region}:${this.account}:secret:songwriter/${config.environment}/openai`;

    // =========================================================================
    // API Service
    // =========================================================================
    const apiTaskDefinition = new ecs.FargateTaskDefinition(this, 'APITaskDef', {
      family: `${prefix}-api`,
      cpu: config.services.api.cpu,
      memoryLimitMiB: config.services.api.memoryMiB,
      executionRole: props.ecsTaskExecutionRole,
      taskRole: props.ecsTaskRole,
    });

    const apiContainer = apiTaskDefinition.addContainer('api', {
      image: ecs.ContainerImage.fromEcrRepository(props.apiRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup: props.apiLogGroup,
        streamPrefix: 'api',
      }),
      environment: {
        ENVIRONMENT: config.environment,
        LLM_PROVIDER: 'openai',
        LLM_MODEL: 'gpt-4o',
        UPLOAD_DIR: '/tmp/uploads',
        VECTOR_STORE_DIR: '/tmp/vectors',
        CORS_ALLOW_ALL: 'false',
        S3_BUCKET: props.uploadsBucketName,
      },
      secrets: {
        DATABASE_URL: ecs.Secret.fromSecretsManager(connectionStringsSecret, 'DATABASE_URL'),
        REDIS_URL: ecs.Secret.fromSecretsManager(connectionStringsSecret, 'REDIS_URL'),
      },
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8081/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },
    });

    apiContainer.addPortMappings({
      containerPort: 8081,
      protocol: ecs.Protocol.TCP,
    });

    this.apiService = new ecs.FargateService(this, 'APIService', {
      serviceName: `${prefix}-api`,
      cluster: props.cluster,
      taskDefinition: apiTaskDefinition,
      desiredCount: config.services.api.desiredCount,
      assignPublicIp: true, // Required for Fargate in public subnets
      securityGroups: [props.ecsSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      circuitBreaker: {
        rollback: true,
      },
      enableExecuteCommand: true,
    });

    this.apiService.attachToApplicationTargetGroup(props.apiTargetGroup);

    // API Auto Scaling
    const apiScaling = this.apiService.autoScaleTaskCount({
      minCapacity: config.services.api.minCapacity,
      maxCapacity: config.services.api.maxCapacity,
    });

    apiScaling.scaleOnCpuUtilization('APICpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(300),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // =========================================================================
    // Web Service
    // =========================================================================
    const webTaskDefinition = new ecs.FargateTaskDefinition(this, 'WebTaskDef', {
      family: `${prefix}-web`,
      cpu: config.services.web.cpu,
      memoryLimitMiB: config.services.web.memoryMiB,
      executionRole: props.ecsTaskExecutionRole,
      taskRole: props.ecsTaskRole,
    });

    const webContainer = webTaskDefinition.addContainer('web', {
      image: ecs.ContainerImage.fromEcrRepository(props.webRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup: props.webLogGroup,
        streamPrefix: 'web',
      }),
      environment: {
        NODE_ENV: 'production',
        // API calls go through ALB path routing
        NEXT_PUBLIC_API_URL: '',
      },
      healthCheck: {
        command: ['CMD-SHELL', 'wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(30),
      },
    });

    webContainer.addPortMappings({
      containerPort: 3000,
      protocol: ecs.Protocol.TCP,
    });

    this.webService = new ecs.FargateService(this, 'WebService', {
      serviceName: `${prefix}-web`,
      cluster: props.cluster,
      taskDefinition: webTaskDefinition,
      desiredCount: config.services.web.desiredCount,
      assignPublicIp: true,
      securityGroups: [props.ecsSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      circuitBreaker: {
        rollback: true,
      },
    });

    this.webService.attachToApplicationTargetGroup(props.webTargetGroup);

    // Web Auto Scaling
    const webScaling = this.webService.autoScaleTaskCount({
      minCapacity: config.services.web.minCapacity,
      maxCapacity: config.services.web.maxCapacity,
    });

    webScaling.scaleOnCpuUtilization('WebCpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(300),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // =========================================================================
    // Worker Service
    // =========================================================================
    const workerTaskDefinition = new ecs.FargateTaskDefinition(this, 'WorkerTaskDef', {
      family: `${prefix}-worker`,
      cpu: config.services.worker.cpu,
      memoryLimitMiB: config.services.worker.memoryMiB,
      executionRole: props.ecsTaskExecutionRole,
      taskRole: props.ecsTaskRole,
    });

    workerTaskDefinition.addContainer('worker', {
      image: ecs.ContainerImage.fromEcrRepository(props.apiRepository, 'latest'), // Same image as API
      command: ['uv', 'run', 'greg', 'worker'],
      logging: ecs.LogDrivers.awsLogs({
        logGroup: props.workerLogGroup,
        streamPrefix: 'worker',
      }),
      environment: {
        ENVIRONMENT: config.environment,
        LLM_PROVIDER: 'openai',
        LLM_MODEL: 'gpt-4o',
        UPLOAD_DIR: '/tmp/uploads',
        VECTOR_STORE_DIR: '/tmp/vectors',
        S3_BUCKET: props.uploadsBucketName,
      },
      secrets: {
        DATABASE_URL: ecs.Secret.fromSecretsManager(connectionStringsSecret, 'DATABASE_URL'),
        REDIS_URL: ecs.Secret.fromSecretsManager(connectionStringsSecret, 'REDIS_URL'),
      },
      // Workers don't have HTTP health checks
    });

    this.workerService = new ecs.FargateService(this, 'WorkerService', {
      serviceName: `${prefix}-worker`,
      cluster: props.cluster,
      taskDefinition: workerTaskDefinition,
      desiredCount: config.services.worker.desiredCount,
      assignPublicIp: true, // Need internet for OpenAI API
      securityGroups: [props.ecsSecurityGroup],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      circuitBreaker: {
        rollback: true,
      },
      enableExecuteCommand: true,
    });

    // Worker Auto Scaling
    const workerScaling = this.workerService.autoScaleTaskCount({
      minCapacity: config.services.worker.minCapacity,
      maxCapacity: config.services.worker.maxCapacity,
    });

    workerScaling.scaleOnCpuUtilization('WorkerCpuScaling', {
      targetUtilizationPercent: 60, // Scale earlier for workers
      scaleInCooldown: cdk.Duration.seconds(300),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, 'APIServiceName', {
      value: this.apiService.serviceName,
    });

    new cdk.CfnOutput(this, 'WebServiceName', {
      value: this.webService.serviceName,
    });

    new cdk.CfnOutput(this, 'WorkerServiceName', {
      value: this.workerService.serviceName,
    });
  }
}
