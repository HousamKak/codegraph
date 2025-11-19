import React from 'react';
import { useStore } from '../store';
import { GraphNode, GraphEdge } from '../types';

export const RightPanel: React.FC = () => {
  const selectedNode = useStore((state) => state.selectedNode);
  const selectedEdge = useStore((state) => state.selectedEdge);

  if (!selectedNode && !selectedEdge) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 p-4 text-center">
        <p>Select a node or edge to view details</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {selectedNode && <NodeInspector node={selectedNode} />}
      {selectedEdge && <EdgeInspector edge={selectedEdge} />}
    </div>
  );
};

const NodeInspector: React.FC<{ node: GraphNode }> = ({ node }) => {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold mb-2 text-gray-800">Node Details</h3>
        <div className="bg-white rounded border border-gray-200 p-3 space-y-2">
          <PropertyRow label="ID" value={node.id} />
          <PropertyRow label="Type" value={node.labels[0]} />
          <PropertyRow label="Name" value={node.properties.name} />

          {node.properties.qualified_name && (
            <PropertyRow label="Qualified Name" value={node.properties.qualified_name} />
          )}

          {node.properties.file_path && (
            <PropertyRow label="File Path" value={node.properties.file_path} />
          )}

          {node.properties.line_number && (
            <PropertyRow label="Line Number" value={String(node.properties.line_number)} />
          )}

          {node.properties.end_line_number && (
            <PropertyRow label="End Line" value={String(node.properties.end_line_number)} />
          )}

          {node.properties.changed !== undefined && (
            <PropertyRow
              label="Changed"
              value={node.properties.changed ? 'Yes' : 'No'}
              highlight={node.properties.changed}
            />
          )}
        </div>
      </div>

      {/* Type-specific properties */}
      {node.labels[0] === 'Function' && (
        <FunctionProperties properties={node.properties} />
      )}

      {node.labels[0] === 'Class' && (
        <ClassProperties properties={node.properties} />
      )}

      {node.labels[0] === 'Variable' && (
        <VariableProperties properties={node.properties} />
      )}

      {node.labels[0] === 'Parameter' && (
        <ParameterProperties properties={node.properties} />
      )}

      {node.labels[0] === 'Type' && (
        <TypeProperties properties={node.properties} />
      )}

      {node.labels[0] === 'CallSite' && (
        <CallSiteProperties properties={node.properties} />
      )}

      {/* Additional properties */}
      {Object.keys(node.properties).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-700">All Properties</h4>
          <div className="bg-gray-50 rounded border border-gray-200 p-3 space-y-1">
            {Object.entries(node.properties)
              .filter(([key]) => !['name', 'qualified_name', 'file_path', 'line_number', 'end_line_number', 'changed'].includes(key))
              .map(([key, value]) => (
                <div key={key} className="text-xs">
                  <span className="font-mono text-gray-600">{key}:</span>{' '}
                  <span className="font-mono text-gray-800">{JSON.stringify(value)}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

const EdgeInspector: React.FC<{ edge: GraphEdge }> = ({ edge }) => {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold mb-2 text-gray-800">Edge Details</h3>
        <div className="bg-white rounded border border-gray-200 p-3 space-y-2">
          <PropertyRow label="ID" value={edge.id || edge.type} />
          <PropertyRow label="Type" value={edge.type} />
          <PropertyRow label="From" value={edge.source} />
          <PropertyRow label="To" value={edge.target} />
        </div>
      </div>

      {edge.properties && Object.keys(edge.properties).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-700">Properties</h4>
          <div className="bg-gray-50 rounded border border-gray-200 p-3 space-y-1">
            {Object.entries(edge.properties).map(([key, value]) => (
              <div key={key} className="text-xs">
                <span className="font-mono text-gray-600">{key}:</span>{' '}
                <span className="font-mono text-gray-800">{JSON.stringify(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const PropertyRow: React.FC<{ label: string; value: string; highlight?: boolean }> = ({
  label,
  value,
  highlight = false
}) => {
  return (
    <div className="flex justify-between items-start text-sm">
      <span className="font-medium text-gray-600">{label}:</span>
      <span className={`font-mono text-right ml-2 ${highlight ? 'text-orange-600 font-semibold' : 'text-gray-800'}`}>
        {value}
      </span>
    </div>
  );
};

const FunctionProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">Function Details</h4>
      <div className="bg-blue-50 rounded border border-blue-200 p-3 space-y-2">
        {properties.is_async && (
          <PropertyRow label="Async" value="Yes" />
        )}
        {properties.is_generator && (
          <PropertyRow label="Generator" value="Yes" />
        )}
        {properties.return_type && (
          <PropertyRow label="Return Type" value={properties.return_type} />
        )}
        {properties.complexity !== undefined && (
          <PropertyRow label="Complexity" value={String(properties.complexity)} />
        )}
      </div>
    </div>
  );
};

const ClassProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">Class Details</h4>
      <div className="bg-purple-50 rounded border border-purple-200 p-3 space-y-2">
        {properties.is_abstract && (
          <PropertyRow label="Abstract" value="Yes" />
        )}
        {properties.bases && properties.bases.length > 0 && (
          <div className="text-sm">
            <span className="font-medium text-gray-600">Base Classes:</span>
            <ul className="ml-4 mt-1 space-y-1">
              {properties.bases.map((base: string, idx: number) => (
                <li key={idx} className="font-mono text-xs text-gray-800">• {base}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

const VariableProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">Variable Details</h4>
      <div className="bg-green-50 rounded border border-green-200 p-3 space-y-2">
        {properties.type_annotation && (
          <PropertyRow label="Type" value={properties.type_annotation} />
        )}
        {properties.scope && (
          <PropertyRow label="Scope" value={properties.scope} />
        )}
        {properties.is_global && (
          <PropertyRow label="Global" value="Yes" />
        )}
      </div>
    </div>
  );
};

const ParameterProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">Parameter Details</h4>
      <div className="bg-yellow-50 rounded border border-yellow-200 p-3 space-y-2">
        {properties.type_annotation && (
          <PropertyRow label="Type" value={properties.type_annotation} />
        )}
        {properties.default_value && (
          <PropertyRow label="Default" value={properties.default_value} />
        )}
        {properties.kind && (
          <PropertyRow label="Kind" value={properties.kind} />
        )}
      </div>
    </div>
  );
};

const TypeProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">Type Details</h4>
      <div className="bg-pink-50 rounded border border-pink-200 p-3 space-y-2">
        {properties.base_type && (
          <PropertyRow label="Base Type" value={properties.base_type} />
        )}
        {properties.type_params && properties.type_params.length > 0 && (
          <div className="text-sm">
            <span className="font-medium text-gray-600">Type Parameters:</span>
            <ul className="ml-4 mt-1 space-y-1">
              {properties.type_params.map((param: string, idx: number) => (
                <li key={idx} className="font-mono text-xs text-gray-800">• {param}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

const CallSiteProperties: React.FC<{ properties: Record<string, any> }> = ({ properties }) => {
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2 text-gray-700">CallSite Details</h4>
      <div className="bg-red-50 rounded border border-red-200 p-3 space-y-2">
        {properties.callee_name && (
          <PropertyRow label="Callee" value={properties.callee_name} />
        )}
        {properties.resolution_status && (
          <PropertyRow label="Resolution" value={properties.resolution_status} />
        )}
        {properties.arg_count !== undefined && (
          <PropertyRow label="Arguments" value={String(properties.arg_count)} />
        )}
      </div>
    </div>
  );
};
