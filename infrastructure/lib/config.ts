/**
 * Environment configuration for Songwriter infrastructure.
 */

export type Environment = 'dev' | 'staging' | 'prod';

export interface EnvironmentConfig {
  /** Environment name */
  environment: Environment;

  /** AWS account ID */
  account: string;

  /** AWS region */
  region: string;

  /** VPC CIDR block */
  vpcCidr: string;

  /** Database configuration */
  database: {
    instanceClass: string;
    allocatedStorage: number;
    multiAz: boolean;
    deletionProtection: boolean;
  };

  /** Redis configuration */
  redis: {
    nodeType: string;
  };

  /** ECS service configuration */
  services: {
    api: ServiceConfig;
    web: ServiceConfig;
    worker: ServiceConfig;
  };

  /** Domain configuration (optional) */
  domain?: {
    name: string;
    certificateArn?: string;
  };
}

export interface ServiceConfig {
  cpu: number;
  memoryMiB: number;
  desiredCount: number;
  minCapacity: number;
  maxCapacity: number;
}

/**
 * Configuration for each environment.
 * Customize these values for your deployment.
 */
export const environments: Record<Environment, Omit<EnvironmentConfig, 'account' | 'region'>> = {
  dev: {
    environment: 'dev',
    vpcCidr: '10.0.0.0/16',
    database: {
      instanceClass: 'db.t4g.micro',
      allocatedStorage: 20,
      multiAz: false,
      deletionProtection: false,
    },
    redis: {
      nodeType: 'cache.t4g.micro',
    },
    services: {
      api: {
        cpu: 512,
        memoryMiB: 1024,
        desiredCount: 1,
        minCapacity: 1,
        maxCapacity: 4,
      },
      web: {
        cpu: 256,
        memoryMiB: 512,
        desiredCount: 1,
        minCapacity: 1,
        maxCapacity: 4,
      },
      worker: {
        cpu: 512,
        memoryMiB: 1024,
        desiredCount: 1,
        minCapacity: 1,
        maxCapacity: 3,
      },
    },
  },

  staging: {
    environment: 'staging',
    vpcCidr: '10.1.0.0/16',
    database: {
      instanceClass: 'db.t4g.small',
      allocatedStorage: 50,
      multiAz: false,
      deletionProtection: true,
    },
    redis: {
      nodeType: 'cache.t4g.small',
    },
    services: {
      api: {
        cpu: 512,
        memoryMiB: 1024,
        desiredCount: 2,
        minCapacity: 1,
        maxCapacity: 6,
      },
      web: {
        cpu: 256,
        memoryMiB: 512,
        desiredCount: 2,
        minCapacity: 1,
        maxCapacity: 6,
      },
      worker: {
        cpu: 1024,
        memoryMiB: 2048,
        desiredCount: 2,
        minCapacity: 1,
        maxCapacity: 4,
      },
    },
  },

  prod: {
    environment: 'prod',
    vpcCidr: '10.2.0.0/16',
    database: {
      instanceClass: 'db.t4g.medium',
      allocatedStorage: 100,
      multiAz: true,
      deletionProtection: true,
    },
    redis: {
      nodeType: 'cache.t4g.medium',
    },
    services: {
      api: {
        cpu: 1024,
        memoryMiB: 2048,
        desiredCount: 2,
        minCapacity: 2,
        maxCapacity: 10,
      },
      web: {
        cpu: 512,
        memoryMiB: 1024,
        desiredCount: 2,
        minCapacity: 2,
        maxCapacity: 10,
      },
      worker: {
        cpu: 1024,
        memoryMiB: 2048,
        desiredCount: 2,
        minCapacity: 1,
        maxCapacity: 5,
      },
    },
  },
};

/**
 * Get full configuration for an environment.
 */
export function getConfig(
  environment: Environment,
  account: string,
  region: string
): EnvironmentConfig {
  return {
    ...environments[environment],
    account,
    region,
  };
}
