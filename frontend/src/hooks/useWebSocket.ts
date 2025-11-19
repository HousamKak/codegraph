/**
 * React hook for managing WebSocket connection and real-time updates
 */

import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store';
import { getWebSocket, type FileChangeMessage, type FileErrorMessage } from '../api/websocket';
import { api } from '../api/client';

export function useWebSocket() {
  const { setWsConnected, setLastFileChange, setError, setGraphData, setValidationReport } = useStore();

  const wsRef = useRef(getWebSocket());

  // Handle file change events
  const handleFileChange = useCallback(
    async (data: FileChangeMessage) => {
      console.log('[Real-time] File changed:', data.file_path);

      // Update last file change
      setLastFileChange(data.file_path);

      // Show validation errors if any
      if (data.validation && !data.validation.is_valid) {
        setError(
          `Validation errors in ${data.file_path}: ${data.validation.errors} error(s), ${data.validation.warnings} warning(s)`
        );

        // Update validation report
        setValidationReport({
          total_violations: data.validation.errors + data.validation.warnings,
          errors: data.validation.errors,
          warnings: data.validation.warnings,
          by_type: {},
          violations: data.validation.violations.map((v) => ({
            violation_type: v.type,
            severity: (v.severity === 'warning' ? 'warning' : 'error'),
            entity_id: '',
            message: v.message,
            file_path: v.file_path || '',
            line_number: v.line_number || 0,
            column_number: 0,
            code_snippet: undefined,
            suggested_fix: undefined,
            details: {},
          })),
          summary: {
            signature_conservation: 0,
            reference_integrity: 0,
            data_flow_consistency: 0,
            structural_integrity: 0,
          },
        });
      } else {
        // Clear error if validation passed
        setError(null);
      }

      // Reload graph to get latest state
      try {
        const updatedGraph = await api.getGraph();
        setGraphData(updatedGraph);
        console.log('[Real-time] Graph refreshed after file change');
      } catch (error) {
        console.error('[Real-time] Error refreshing graph:', error);
      }
    },
    [setLastFileChange, setError, setValidationReport, setGraphData]
  );

  // Handle file error events
  const handleFileError = useCallback(
    (data: FileErrorMessage) => {
      console.error('[Real-time] File error:', data.file_path, data.error);
      setError(`Error processing ${data.file_path}: ${data.error}`);
    },
    [setError]
  );

  useEffect(() => {
    const ws = wsRef.current;

    // Register event listeners
    ws.on('connected', () => {
      console.log('[Real-time] WebSocket connected');
      setWsConnected(true);
    });

    ws.on('file_changed', (data) => {
      handleFileChange(data as FileChangeMessage);
    });

    ws.on('file_error', (data) => {
      handleFileError(data as FileErrorMessage);
    });

    // Connect
    ws.connect();

    // Set up ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.isConnected()) {
        ws.ping();
      }
    }, 30000); // Ping every 30 seconds

    // Cleanup
    return () => {
      clearInterval(pingInterval);
      ws.disconnect();
      setWsConnected(false);
    };
  }, [setWsConnected, handleFileChange, handleFileError]);

  return {
    ws: wsRef.current,
  };
}
