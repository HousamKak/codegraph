import { useCallback, useEffect, useMemo, useState } from 'react';
import AutoSizer from 'react-virtualized-auto-sizer';
import { FixedSizeList as List, ListChildComponentProps } from 'react-window';
import { api } from '../api/client';
import type { ValidationReport, ValidationLawReport, Violation } from '../types';

const LAW_METADATA = [
  {
    key: 'structural',
    title: 'S Law (Structural Validity)',
    description: 'Graph structure must conform to schema constraints and edge rules.',
    color: 'blue',
  },
  {
    key: 'reference',
    title: 'R Law (Referential Coherence)',
    description: 'Every identifier must resolve to a unique declaration that is visible in scope.',
    color: 'purple',
  },
  {
    key: 'typing',
    title: 'T Law (Semantic Typing)',
    description: 'Argument, return, and assignment types must be compatible under the type rules.',
    color: 'green',
  },
] as const;

const ROW_HEIGHT = 88;

type LawKey = (typeof LAW_METADATA)[number]['key'];

type ViolationRowData = {
  violations: Violation[];
};

const ViolationRow = ({ index, style, data }: ListChildComponentProps<ViolationRowData>) => {
  const violation = data.violations[index];
  return (
    <div style={style} className="px-3 py-2 border-b border-white/5 text-sm text-gray-200">
      <div className="font-semibold text-white">{violation.message}</div>
      <div className="text-xs text-gray-400 mt-1">
        {violation.violation_type} • {violation.severity.toUpperCase()} • {violation.entity_id}
      </div>
      {violation.file_path && (
        <div className="text-xs text-gray-500 mt-1">
          {violation.file_path}:L{violation.line_number ?? '?'}
        </div>
      )}
      {violation.details?.function && (
        <div className="text-xs text-gray-400 mt-1">Function: {violation.details.function}</div>
      )}
    </div>
  );
};

export const ValidationView: React.FC = () => {
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [lawReports, setLawReports] = useState<Record<string, ValidationLawReport>>({});
  const [loading, setLoading] = useState(false);
  const [loadingLaw, setLoadingLaw] = useState<LawKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    structural: true,
    reference: true,
    typing: true,
  });

  const loadValidation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.validate();
      setValidation(result);
      if (result.laws) {
        setLawReports(result.laws);
      } else {
        setLawReports(buildLawReportsFromViolations(result.violations));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load validation results');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadValidation();
  }, [loadValidation]);

  const toggleSection = (key: LawKey) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const runLaw = async (law: LawKey) => {
    setLoadingLaw(law);
    setError(null);
    try {
      let report: ValidationLawReport;
      if (law === 'structural') {
        report = await api.validateStructural();
      } else if (law === 'reference') {
        report = await api.validateReference();
      } else {
        report = await api.validateTyping();
      }
      setLawReports((prev) => ({ ...prev, [law]: report }));
      setValidation((prev) => (prev ? { ...prev, laws: { ...(prev.laws || {}), [law]: report } } : prev));
    } catch (err: any) {
      setError(err.message || 'Failed to run validation');
    } finally {
      setLoadingLaw(null);
    }
  };

  const combinedLawReports = useMemo(() => {
    const fromValidation = validation?.laws ?? {};
    const fallback = validation ? buildLawReportsFromViolations(validation.violations) : {};
    return LAW_METADATA.reduce<Record<string, ValidationLawReport>>((acc, law) => {
      acc[law.key] = lawReports[law.key] || fromValidation[law.key] || fallback[law.key] || {
        law: law.key,
        total_violations: 0,
        errors: 0,
        warnings: 0,
        by_type: {},
        violations: [],
      };
      return acc;
    }, {});
  }, [lawReports, validation]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-500">Running validation...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  if (!validation) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        No validation results yet.
      </div>
    );
  }

  const overallStatus = validation.total_violations === 0;

  return (
    <div className="h-full flex flex-col bg-gray-50 text-gray-100">
      <div className="bg-[#1f1f1f] border-b border-black/50 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Conservation Law Validation</h2>
            <p className="text-sm text-gray-400">Last run detected {validation.total_violations} violation(s).</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadValidation}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm"
            >
              Run All
            </button>
            {LAW_METADATA.map((law) => (
              <button
                key={law.key}
                onClick={() => runLaw(law.key)}
                className={`px-3 py-1.5 rounded text-sm ${
                  loadingLaw === law.key
                    ? 'bg-gray-600 text-white cursor-wait'
                    : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                }`}
                disabled={loadingLaw === law.key}
              >
                Run {law.title.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 text-sm">
          {overallStatus ? (
            <span className="text-green-400 font-semibold">Graph is valid</span>
          ) : (
            <span className="text-red-400 font-semibold">
              {validation.errors} errors / {validation.warnings} warnings
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#121212]">
        {LAW_METADATA.map((law) => (
          <LawSection
            key={law.key}
            title={law.title}
            description={law.description}
            color={law.color}
            expanded={!!expandedSections[law.key]}
            onToggle={() => toggleSection(law.key)}
            report={combinedLawReports[law.key]}
          />
        ))}
      </div>
    </div>
  );
};

interface LawSectionProps {
  title: string;
  description: string;
  color: 'blue' | 'purple' | 'green';
  expanded: boolean;
  onToggle: () => void;
  report: ValidationLawReport;
}

const LawSection = ({ title, description, color, expanded, onToggle, report }: LawSectionProps) => {
  const hasViolations = report.violations.length > 0;
  const bodyHeight = expanded ? Math.min(report.violations.length * ROW_HEIGHT, 320) : 0;
  const borderColor = color === 'blue' ? 'border-blue-500' : color === 'purple' ? 'border-purple-500' : 'border-green-500';

  return (
    <div className={`bg-[#1b1b1b] rounded-lg border ${borderColor} shadow-lg`}>
      <button
        className="w-full text-left px-4 py-3 flex items-center justify-between"
        onClick={onToggle}
      >
        <div>
          <div className="text-white font-semibold">{title}</div>
          <div className="text-xs text-gray-400">{description}</div>
        </div>
        <div className="text-sm text-gray-300">
          {report.total_violations} violation(s)
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {!hasViolations ? (
            <div className="text-sm text-gray-400">No violations detected.</div>
          ) : (
            <div className="mt-2" style={{ height: bodyHeight }}>
              <AutoSizer>
                {({ height, width }) => (
                  <List
                    height={height}
                    width={width}
                    itemCount={report.violations.length}
                    itemSize={ROW_HEIGHT}
                    itemData={{ violations: report.violations } as ViolationRowData}
                  >
                    {ViolationRow}
                  </List>
                )}
              </AutoSizer>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function buildLawReportsFromViolations(
  violations: Violation[]
): Record<string, ValidationLawReport> {
  const groups: Record<string, Violation[]> = {
    structural: [],
    reference: [],
    typing: [],
  };

  violations.forEach((violation) => {
    if (violation.violation_type.includes('reference')) {
      groups.reference.push(violation);
    } else if (violation.violation_type.includes('type')) {
      groups.typing.push(violation);
    } else {
      groups.structural.push(violation);
    }
  });

  return Object.fromEntries(
    Object.entries(groups).map(([key, list]) => [
      key,
      {
        law: key,
        total_violations: list.length,
        errors: list.filter((v) => v.severity === 'error').length,
        warnings: list.filter((v) => v.severity === 'warning').length,
        by_type: list.reduce<Record<string, number>>((acc, violation) => {
          acc[violation.violation_type] = (acc[violation.violation_type] || 0) + 1;
          return acc;
        }, {}),
        violations: list,
      },
    ])
  );
}
