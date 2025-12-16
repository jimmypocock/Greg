/**
 * WebSocket hook for real-time agent task updates.
 *
 * Connects to the backend WebSocket endpoint and streams agent events
 * to provide real-time feedback during long-running agent tasks.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AgentEvent, AgentEventData, AgentTaskResult } from '@/types/agent';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8081';

export type AgentStatus = 'idle' | 'connecting' | 'running' | 'completed' | 'failed';

export interface AgentProgress {
  status: AgentStatus;
  agentName?: string;
  taskDescription?: string;
  currentActivity?: string;
  thoughts: string[];
  toolsUsed: Array<{ name: string; output?: string }>;
  streamedText: string;  // Accumulated streamed text from agent.chunk events
  result?: AgentTaskResult;
  error?: string;
}

interface UseAgentWebSocketOptions {
  onEvent?: (event: AgentEvent) => void;
  onComplete?: (result: AgentTaskResult) => void;
  onError?: (error: string) => void;
}

export function useAgentWebSocket(options: UseAgentWebSocketOptions = {}) {
  const { onEvent, onComplete, onError } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<AgentProgress>({
    status: 'idle',
    thoughts: [],
    toolsUsed: [],
    streamedText: '',
  });

  const reset = useCallback(() => {
    setProgress({
      status: 'idle',
      thoughts: [],
      toolsUsed: [],
      streamedText: '',
    });
    setTaskId(null);
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(
    (newTaskId: string) => {
      // Close existing connection
      disconnect();

      setTaskId(newTaskId);
      setProgress({
        status: 'connecting',
        thoughts: [],
        toolsUsed: [],
        streamedText: '',
      });

      const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${newTaskId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setProgress((prev) => ({ ...prev, status: 'running' }));
      };

      ws.onmessage = (event) => {
        try {
          const agentEvent: AgentEvent = JSON.parse(event.data);
          onEvent?.(agentEvent);

          const data = agentEvent.data;

          switch (agentEvent.event) {
            case 'agent.started':
              setProgress((prev) => ({
                ...prev,
                status: 'running',
                agentName: data.agent_name,
                taskDescription: data.task_description,
                currentActivity: `${data.agent_name} starting ${data.task_description}...`,
              }));
              break;

            case 'agent.thinking':
              if (data.thought) {
                setProgress((prev) => ({
                  ...prev,
                  currentActivity: data.thought!.slice(0, 100),
                  thoughts: [...prev.thoughts, data.thought!].slice(-20), // Keep last 20
                }));
              }
              break;

            case 'agent.chunk':
              // Streaming text chunk from the agent
              if (data.text) {
                setProgress((prev) => ({
                  ...prev,
                  currentActivity: 'Writing response...',
                  streamedText: prev.streamedText + data.text,
                }));
              }
              break;

            case 'agent.tool.start':
              setProgress((prev) => ({
                ...prev,
                currentActivity: `Using tool: ${data.tool_name}`,
                toolsUsed: [...prev.toolsUsed, { name: data.tool_name! }],
              }));
              break;

            case 'agent.tool.end':
              setProgress((prev) => {
                const tools = [...prev.toolsUsed];
                const lastIndex = tools.findLastIndex((t) => t.name === data.tool_name);
                if (lastIndex >= 0) {
                  tools[lastIndex] = { ...tools[lastIndex], output: data.tool_output };
                }
                return {
                  ...prev,
                  currentActivity: `Completed: ${data.tool_name}`,
                  toolsUsed: tools,
                };
              });
              break;

            case 'agent.completed':
              const result: AgentTaskResult = {
                success: true,
                result: data.result || '',
                duration_ms: data.duration_ms || 0,
                input_tokens: 0,
                output_tokens: 0,
                total_cost_usd: '0',
              };
              setProgress((prev) => ({
                ...prev,
                status: 'completed',
                currentActivity: 'Complete',
                result,
              }));
              onComplete?.(result);
              ws.close();
              break;

            case 'agent.failed':
              setProgress((prev) => ({
                ...prev,
                status: 'failed',
                currentActivity: 'Failed',
                error: data.error,
              }));
              onError?.(data.error || 'Unknown error');
              ws.close();
              break;
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setProgress((prev) => ({
          ...prev,
          status: 'failed',
          error: 'WebSocket connection error',
        }));
        onError?.('WebSocket connection error');
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    },
    [disconnect, onEvent, onComplete, onError]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    taskId,
    progress,
    connect,
    disconnect,
    reset,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
