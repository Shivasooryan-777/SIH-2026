import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { ChevronDown, Check, Search, X } from 'lucide-react';

export interface ComboboxOption {
  value: string | number;
  label: string;
  sublabel?: string;
  group?: string;
}

interface ComboboxProps {
  label: string;
  options: ComboboxOption[];
  value: string | number | null;
  onChange: (val: string | number) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
}

export const Combobox: React.FC<ComboboxProps> = ({
  label,
  options,
  value,
  onChange,
  placeholder = 'Select option...',
  disabled = false,
  required = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const shouldReduceMotion = useReducedMotion();

  const selectedOption = (options || []).find((opt) => opt.value === value);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search when opening
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
    if (!isOpen) {
      setSearchQuery('');
    }
  }, [isOpen]);

  // Filter options by search query
  const filteredOptions = (options || []).filter((opt) => {
    const q = searchQuery.toLowerCase();
    return (
      (opt.label || '').toLowerCase().includes(q) ||
      (opt.sublabel && opt.sublabel.toLowerCase().includes(q)) ||
      (opt.group && opt.group.toLowerCase().includes(q))
    );
  });

  // Group filtered options
  const groupedOptions = filteredOptions.reduce<Record<string, ComboboxOption[]>>((acc, opt) => {
    const grp = opt.group || 'General';
    if (!acc[grp]) acc[grp] = [];
    acc[grp].push(opt);
    return acc;
  }, {});

  return (
    <div className="relative w-full text-left" ref={containerRef}>
      <label className="block text-xs font-medium text-text-secondary mb-1.5 flex items-center justify-between">
        <span>
          {label} {required && <span className="text-accent">*</span>}
        </span>
        {selectedOption?.sublabel && (
          <span className="text-[11px] font-mono text-text-tertiary">
            {selectedOption.sublabel}
          </span>
        )}
      </label>

      {/* Trigger Button - rounded-2xl, 1px border #26262B */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        title={selectedOption ? `${selectedOption.label}${selectedOption.sublabel ? ` — ${selectedOption.sublabel}` : ''}` : placeholder}
        className={`w-full h-11 px-3.5 rounded-2xl bg-[#131316] border transition-all duration-200 flex items-center justify-between gap-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent ${
          isOpen ? 'border-accent ring-1 ring-accent' : 'border-[#26262B] hover:border-[#3F3F46]'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span
          title={selectedOption ? selectedOption.label : placeholder}
          className={`truncate ${selectedOption ? 'text-text-primary font-medium' : 'text-text-tertiary'}`}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-text-secondary transition-transform duration-200 shrink-0 ${
            isOpen ? 'rotate-180 text-accent' : ''
          }`}
        />
      </button>

      {/* Floating Menu Panel - rounded-2xl, 1px border #26262B, backdrop-blur */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: -6 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
            className="absolute z-50 left-0 right-0 mt-2 p-2 rounded-2xl bg-[#131316]/95 backdrop-blur-md border border-[#26262B] shadow-2xl overflow-hidden"
          >
            {/* Search Box */}
            <div className="relative mb-2 px-1">
              <Search className="w-3.5 h-3.5 text-text-tertiary absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full h-8 pl-8 pr-7 rounded-xl bg-[#09090B] border border-[#26262B] text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Options List */}
            <div className="max-h-56 overflow-y-auto space-y-3 px-1 py-0.5">
              {Object.keys(groupedOptions).length === 0 ? (
                <div className="py-4 text-center text-xs text-text-tertiary">
                  No matching options found
                </div>
              ) : (
                Object.entries(groupedOptions).map(([groupName, groupItems]) => (
                  <div key={groupName} className="space-y-1">
                    {groupName !== 'General' && (
                      <div className="px-2 py-1 text-[10px] font-semibold tracking-wider uppercase text-text-tertiary">
                        {groupName}
                      </div>
                    )}
                    {groupItems.map((item) => {
                      const isSelected = item.value === value;
                      return (
                        <div
                          key={item.value}
                          title={item.sublabel ? `${item.label} — ${item.sublabel}` : item.label}
                          onClick={() => {
                            onChange(item.value);
                            setIsOpen(false);
                          }}
                          className={`w-full px-2.5 py-2 rounded-xl text-xs flex items-center justify-between cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-[#1C1C21] text-accent font-medium'
                              : 'text-text-primary hover:bg-[#1C1C21]'
                          }`}
                        >
                          <div className="flex flex-col truncate">
                            <span className="truncate">{item.label}</span>
                            {item.sublabel && (
                              <span className="text-[10px] font-mono text-text-tertiary">
                                {item.sublabel}
                              </span>
                            )}
                          </div>
                          {isSelected && <Check className="w-3.5 h-3.5 text-accent shrink-0 ml-2" />}
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
