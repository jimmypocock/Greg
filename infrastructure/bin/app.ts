#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FoundationStack } from '../lib/stacks/foundation-stack';
import { DataStack } from '../lib/stacks/data-stack';
import { PlatformStack } from '../lib/stacks/platform-stack';
import { ServicesStack } from '../lib/stacks/services-stack';
import { getConfig, Environment } from '../lib/config';

/**
 * Songwriter CDK Application
 *
 * Deploys infrastructure in layers:
 * 1. Foundation - VPC, Security Groups, IAM
 * 2. Data - RDS, Redis, S3
 * 3. Platform - ECS Cluster, ALB, ECR
 * 4. Services - API, Web, Worker
 *
 * Usage:
 *   # Deploy all stacks to dev
 *   cdk deploy --all -c environment=dev
 *
 *   # Deploy specific stack
 *   cdk deploy Songwriter-dev-Services -c environment=dev
 *
 *   # Diff before deploy
 *   cdk diff --all -c environment=dev
 *
 *   # Destroy (careful!)
 *   cdk destroy --all -c environment=dev
 */

const app = new cdk.App();

// Get environment from context
const environment = (app.node.tryGetContext('environment') || 'dev') as Environment;

// Get AWS account and region from environment or defaults
const account = process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID;
const region = process.env.CDK_DEFAULT_REGION || process.env.AWS_REGION || 'us-east-1';

if (!account) {
  console.error('Error: AWS account not found. Set CDK_DEFAULT_ACCOUNT or AWS_ACCOUNT_ID');
  process.exit(1);
}

// Load configuration
const config = getConfig(environment, account, region);

console.log(`Deploying Songwriter infrastructure for environment: ${environment}`);
console.log(`Account: ${account}, Region: ${region}`);

// Stack naming convention: Songwriter-{env}-{layer}
const stackPrefix = `Songwriter-${environment}`;

// Common stack props
const stackProps: cdk.StackProps = {
  env: {
    account: config.account,
    region: config.region,
  },
  tags: {
    Project: 'Songwriter',
    Environment: environment,
    ManagedBy: 'CDK',
  },
};

// ============================================================================
// Layer 1: Foundation
// ============================================================================
const foundationStack = new FoundationStack(app, `${stackPrefix}-Foundation`, {
  ...stackProps,
  config,
  description: `Songwriter ${environment} - VPC, Security Groups, IAM Roles`,
});

// ============================================================================
// Layer 2: Data
// ============================================================================
const dataStack = new DataStack(app, `${stackPrefix}-Data`, {
  ...stackProps,
  config,
  vpc: foundationStack.vpc,
  databaseSecurityGroup: foundationStack.databaseSecurityGroup,
  description: `Songwriter ${environment} - RDS, ElastiCache, S3`,
});
dataStack.addDependency(foundationStack);

// ============================================================================
// Layer 3: Platform
// ============================================================================
const platformStack = new PlatformStack(app, `${stackPrefix}-Platform`, {
  ...stackProps,
  config,
  vpc: foundationStack.vpc,
  albSecurityGroup: foundationStack.albSecurityGroup,
  description: `Songwriter ${environment} - ECS Cluster, ALB, ECR`,
});
platformStack.addDependency(foundationStack);

// ============================================================================
// Layer 4: Services
// ============================================================================
const servicesStack = new ServicesStack(app, `${stackPrefix}-Services`, {
  ...stackProps,
  config,
  vpc: foundationStack.vpc,
  ecsSecurityGroup: foundationStack.ecsSecurityGroup,
  ecsTaskExecutionRole: foundationStack.ecsTaskExecutionRole,
  ecsTaskRole: foundationStack.ecsTaskRole,
  cluster: platformStack.cluster,
  apiTargetGroup: platformStack.apiTargetGroup,
  webTargetGroup: platformStack.webTargetGroup,
  apiRepository: platformStack.apiRepository,
  webRepository: platformStack.webRepository,
  apiLogGroup: platformStack.apiLogGroup,
  webLogGroup: platformStack.webLogGroup,
  workerLogGroup: platformStack.workerLogGroup,
  databaseSecretArn: dataStack.databaseSecret.secretArn,
  connectionStringsSecretArn: dataStack.connectionStringsSecret.secretArn,
  uploadsBucketName: dataStack.uploadsBucket.bucketName,
  description: `Songwriter ${environment} - API, Web, Worker Services`,
});
servicesStack.addDependency(dataStack);
servicesStack.addDependency(platformStack);

// ============================================================================
// Synthesize
// ============================================================================
app.synth();
