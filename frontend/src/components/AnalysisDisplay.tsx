import React, { useEffect, useRef } from 'react';

interface AnalysisDisplayProps {
  tokens: string[];
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ tokens }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new tokens arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [tokens]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '400px',
        backgroundColor: '#f9f9f9',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '1rem',
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: '0.9rem',
        lineHeight: '1.6',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}
    >
      {tokens.length > 0 ? (
        <div>{tokens.join('')}</div>
      ) : (
        <div style={{ color: '#999', textAlign: 'center', marginTop: '2rem' }}>
          等待AI分析结果...
        </div>
      )}
    </div>
  );
};

export default AnalysisDisplay;
