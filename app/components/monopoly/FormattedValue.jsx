import React from 'react';

export const FormattedValue = ({ value, type = 'currency', prefix = '$', ...props }) => {
  const formatValue = () => {
    const num = parseFloat(value);
    
    // Fallback if the value isn't a valid number
    if (isNaN(num)) return '0';

    // --- CURRENCY CONVERSION ---
    if (type === 'currency') {
      const absValue = Math.abs(num);
      const sign = num < 0 ? '-' : '';

      if (absValue < 100000) {
        return `${sign}${prefix}${absValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}`; // Below 100,000 $
      }
      if (absValue < 1000000) {
        return `${sign}${prefix}${(absValue / 1000).toFixed(2).replace(/\.00$/, '')}K`; // Below 1,000,000 $
      }
      if (absValue < 1000000000) {
        return `${sign}${prefix}${(absValue / 1000000).toFixed(3).replace(/\.00$/, '')}M`; // Below 1,000,000,000 $
      }
      return `${sign}${prefix}${(absValue / 1000000000).toFixed(3).replace(/\.00$/, '')}B`;  // Above 1,000,000,000 $
    }

    // --- TIME CONVERSION ---
    if (type === 'time') {
      if (num >= 86400) {
        const days = Math.floor(num / 86400);
        return `${days}D`;
      }

      const hours = Math.floor(num / 3600);
      const minutes = Math.floor((num % 3600) / 60);
      const seconds = Math.floor(num % 60);

      const ss = String(seconds).padStart(2, '0');

      if (minutes > 0) {
        const mm = String(minutes).padStart(2, '0');
        return `${mm}:${ss}`;
      }

      if (hours > 0) {
        const hh = String(hours).padStart(2, '0');
        return `${hh}:${mm}:${ss}`;
      }

      return `${ss}S`;
    }

    return num.toString();
  };

  return (
    <span className="tabular-nums" {...props}>
      {formatValue()}
    </span>
  );
};