import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config';

export interface DataStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  databaseSecurityGroup: ec2.ISecurityGroup;
}

/**
 * Data Stack - RDS PostgreSQL, ElastiCache Redis, S3
 *
 * Stateful resources with RemovalPolicy.RETAIN to prevent accidental deletion.
 */
export class DataStack extends cdk.Stack {
  public readonly database: rds.IDatabaseInstance;
  public readonly databaseSecret: secretsmanager.ISecret;
  public readonly redisCluster: elasticache.CfnCacheCluster;
  public readonly uploadsBucket: s3.IBucket;
  public readonly connectionStringsSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    const { config, vpc, databaseSecurityGroup } = props;
    const prefix = `songwriter-${config.environment}`;

    // =========================================================================
    // Secrets Manager - Database credentials
    // =========================================================================
    this.databaseSecret = new secretsmanager.Secret(this, 'DBCredentials', {
      secretName: `songwriter/${config.environment}/db-credentials`,
      description: 'RDS PostgreSQL credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'songwriter' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    // =========================================================================
    // RDS PostgreSQL
    // =========================================================================
    const dbSubnetGroup = new rds.SubnetGroup(this, 'DBSubnetGroup', {
      vpc,
      description: 'Subnet group for RDS',
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC, // Using public for cost savings
      },
    });

    this.database = new rds.DatabaseInstance(this, 'Database', {
      instanceIdentifier: prefix,
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16_4,
      }),
      instanceType: new ec2.InstanceType(config.database.instanceClass),
      vpc,
      subnetGroup: dbSubnetGroup,
      securityGroups: [databaseSecurityGroup],
      credentials: rds.Credentials.fromSecret(this.databaseSecret),
      databaseName: 'songwriter',
      allocatedStorage: config.database.allocatedStorage,
      storageType: rds.StorageType.GP3,
      multiAz: config.database.multiAz,
      deletionProtection: config.database.deletionProtection,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Never delete database
      backupRetention: config.environment === 'prod'
        ? cdk.Duration.days(7)
        : cdk.Duration.days(1),
      enablePerformanceInsights: config.environment === 'prod',
      publiclyAccessible: false,
    });

    // =========================================================================
    // ElastiCache Redis
    // =========================================================================
    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      cacheSubnetGroupName: `${prefix}-redis-subnet`,
      description: 'Subnet group for Redis',
      subnetIds: vpc.publicSubnets.map((subnet) => subnet.subnetId),
    });

    this.redisCluster = new elasticache.CfnCacheCluster(this, 'RedisCluster', {
      clusterName: prefix,
      engine: 'redis',
      engineVersion: '7.1',
      cacheNodeType: config.redis.nodeType,
      numCacheNodes: 1,
      cacheSubnetGroupName: redisSubnetGroup.cacheSubnetGroupName,
      vpcSecurityGroupIds: [databaseSecurityGroup.securityGroupId],
    });
    this.redisCluster.addDependency(redisSubnetGroup);

    // =========================================================================
    // S3 Bucket
    // =========================================================================
    this.uploadsBucket = new s3.Bucket(this, 'UploadsBucket', {
      bucketName: `${prefix}-uploads-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Never delete files
      autoDeleteObjects: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'DeleteTempFiles',
          prefix: 'temp/',
          expiration: cdk.Duration.days(1),
        },
        {
          id: 'TransitionOldFiles',
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
      cors: [
        {
          allowedHeaders: ['*'],
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
          ],
          allowedOrigins: ['*'], // Restrict in production via CloudFront
          maxAge: 3000,
        },
      ],
    });

    // =========================================================================
    // Connection Strings Secret
    // =========================================================================
    // This will be populated after we know all endpoints
    this.connectionStringsSecret = new secretsmanager.Secret(this, 'ConnectionStrings', {
      secretName: `songwriter/${config.environment}/connection-strings`,
      description: 'Database and Redis connection strings',
    });

    // We need to create a custom resource or use a Lambda to update this
    // For now, we'll output the values and they can be set manually or via CLI

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, 'DBEndpoint', {
      value: this.database.dbInstanceEndpointAddress,
      exportName: `${prefix}-db-endpoint`,
    });

    new cdk.CfnOutput(this, 'DBSecretArn', {
      value: this.databaseSecret.secretArn,
      exportName: `${prefix}-db-secret-arn`,
    });

    new cdk.CfnOutput(this, 'RedisEndpoint', {
      value: this.redisCluster.attrRedisEndpointAddress,
      exportName: `${prefix}-redis-endpoint`,
    });

    new cdk.CfnOutput(this, 'UploadsBucketName', {
      value: this.uploadsBucket.bucketName,
      exportName: `${prefix}-uploads-bucket`,
    });

    new cdk.CfnOutput(this, 'ConnectionStringsSecretArn', {
      value: this.connectionStringsSecret.secretArn,
      exportName: `${prefix}-connection-strings-secret-arn`,
    });

    // Output the connection string format for manual setup
    new cdk.CfnOutput(this, 'DatabaseURL', {
      value: `postgresql://songwriter:<password>@${this.database.dbInstanceEndpointAddress}:5432/songwriter`,
      description: 'Database URL template (replace <password> with actual password)',
    });

    new cdk.CfnOutput(this, 'RedisURL', {
      value: `redis://${this.redisCluster.attrRedisEndpointAddress}:6379`,
      description: 'Redis URL',
    });
  }
}
