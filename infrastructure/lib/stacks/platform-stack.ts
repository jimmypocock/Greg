import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config';

export interface PlatformStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  vpc: ec2.IVpc;
  albSecurityGroup: ec2.ISecurityGroup;
}

/**
 * Platform Stack - ECS Cluster, ALB, ECR Repositories
 *
 * Shared infrastructure for all services.
 */
export class PlatformStack extends cdk.Stack {
  public readonly cluster: ecs.ICluster;
  public readonly alb: elbv2.IApplicationLoadBalancer;
  public readonly httpListener: elbv2.IApplicationListener;
  public readonly httpsListener?: elbv2.IApplicationListener;
  public readonly apiTargetGroup: elbv2.IApplicationTargetGroup;
  public readonly webTargetGroup: elbv2.IApplicationTargetGroup;
  public readonly apiRepository: ecr.IRepository;
  public readonly webRepository: ecr.IRepository;
  public readonly apiLogGroup: logs.ILogGroup;
  public readonly webLogGroup: logs.ILogGroup;
  public readonly workerLogGroup: logs.ILogGroup;

  constructor(scope: Construct, id: string, props: PlatformStackProps) {
    super(scope, id, props);

    const { config, vpc, albSecurityGroup } = props;
    const prefix = `songwriter-${config.environment}`;

    // =========================================================================
    // ECS Cluster
    // =========================================================================
    this.cluster = new ecs.Cluster(this, 'Cluster', {
      clusterName: prefix,
      vpc,
      containerInsights: true,
      enableFargateCapacityProviders: true,
    });

    // =========================================================================
    // Application Load Balancer
    // =========================================================================
    this.alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      loadBalancerName: `${prefix}-alb`,
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
    });

    // HTTP Listener
    this.httpListener = this.alb.addListener('HTTPListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultAction: elbv2.ListenerAction.fixedResponse(404, {
        contentType: 'text/plain',
        messageBody: 'Not Found',
      }),
    });

    // HTTPS Listener (only if certificate is provided)
    if (config.domain?.certificateArn) {
      this.httpsListener = this.alb.addListener('HTTPSListener', {
        port: 443,
        protocol: elbv2.ApplicationProtocol.HTTPS,
        certificates: [
          elbv2.ListenerCertificate.fromArn(config.domain.certificateArn),
        ],
        sslPolicy: elbv2.SslPolicy.TLS13_RES,
        defaultAction: elbv2.ListenerAction.fixedResponse(404, {
          contentType: 'text/plain',
          messageBody: 'Not Found',
        }),
      });

      // Redirect HTTP to HTTPS when certificate is present
      this.httpListener.addAction('RedirectToHTTPS', {
        priority: 1,
        conditions: [elbv2.ListenerCondition.pathPatterns(['/*'])],
        action: elbv2.ListenerAction.redirect({
          protocol: 'HTTPS',
          port: '443',
          permanent: true,
        }),
      });
    }

    // =========================================================================
    // Target Groups
    // =========================================================================

    // API Target Group
    this.apiTargetGroup = new elbv2.ApplicationTargetGroup(this, 'APITargetGroup', {
      targetGroupName: `${prefix}-api`,
      vpc,
      port: 8081,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // Web Target Group
    this.webTargetGroup = new elbv2.ApplicationTargetGroup(this, 'WebTargetGroup', {
      targetGroupName: `${prefix}-web`,
      vpc,
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
      },
    });

    // =========================================================================
    // Listener Rules
    // =========================================================================
    const apiPaths = [
      '/health',
      '/docs',
      '/docs/*',
      '/openapi.json',
      '/auth/*',
      '/songs/*',
      '/agents/*',
      '/billing/*',
      '/webhooks/*',
      '/admin/*',
      '/ws/*',
      '/collaboration/*',
      '/notes/*',
      '/versions/*',
      '/audio/*',
    ];

    // Add rules to HTTP listener (or HTTPS if available)
    const primaryListener = this.httpsListener || this.httpListener;

    // API routes
    primaryListener.addAction('APIRoutes', {
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(apiPaths)],
      action: elbv2.ListenerAction.forward([this.apiTargetGroup]),
    });

    // Web routes (catch-all)
    primaryListener.addAction('WebRoutes', {
      priority: 100,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/*'])],
      action: elbv2.ListenerAction.forward([this.webTargetGroup]),
    });

    // =========================================================================
    // ECR Repositories
    // =========================================================================
    this.apiRepository = new ecr.Repository(this, 'APIRepository', {
      repositoryName: `${prefix}/api`,
      imageScanOnPush: true,
      lifecycleRules: [
        {
          maxImageCount: 10,
          description: 'Keep last 10 images',
        },
      ],
    });

    this.webRepository = new ecr.Repository(this, 'WebRepository', {
      repositoryName: `${prefix}/web`,
      imageScanOnPush: true,
      lifecycleRules: [
        {
          maxImageCount: 10,
          description: 'Keep last 10 images',
        },
      ],
    });

    // =========================================================================
    // CloudWatch Log Groups
    // =========================================================================
    this.apiLogGroup = new logs.LogGroup(this, 'APILogGroup', {
      logGroupName: `/ecs/${prefix}/api`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    this.webLogGroup = new logs.LogGroup(this, 'WebLogGroup', {
      logGroupName: `/ecs/${prefix}/web`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    this.workerLogGroup = new logs.LogGroup(this, 'WorkerLogGroup', {
      logGroupName: `/ecs/${prefix}/worker`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, 'ClusterArn', {
      value: this.cluster.clusterArn,
      exportName: `${prefix}-cluster-arn`,
    });

    new cdk.CfnOutput(this, 'ALBDnsName', {
      value: this.alb.loadBalancerDnsName,
      description: 'Point your domain CNAME to this address',
      exportName: `${prefix}-alb-dns`,
    });

    new cdk.CfnOutput(this, 'APIRepositoryUri', {
      value: this.apiRepository.repositoryUri,
      exportName: `${prefix}-api-repo-uri`,
    });

    new cdk.CfnOutput(this, 'WebRepositoryUri', {
      value: this.webRepository.repositoryUri,
      exportName: `${prefix}-web-repo-uri`,
    });
  }
}
