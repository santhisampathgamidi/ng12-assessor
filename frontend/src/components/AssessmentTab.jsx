import React, { useState, useEffect, useRef } from 'react'
import { Play, CheckCircle2, Loader2, AlertTriangle, ShieldCheck, Search, Brain, FileText } from 'lucide-react'

const RISK_STYLES = {
  URGENT_REFERRAL: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  VERY_URGENT: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  URGENT_INVESTIGATION: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  SAFETY_NETTING: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
  LOW_RISK: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
}

const STEPS = [
  { icon: FileText, label: 'Retrieving patient records' },
  { icon: Search, label: 'Searching NG12 guideline sections' },
  { icon: Brain, label: 'Matching symptoms against referral criteria' },
  { icon: CheckCircle2, label: 'Generating risk assessment with citations' },
]

function TypewriterText({ text, speed = 8 }) {
  const [displayed, setDisplayed] = useState('')
  const idx = useRef(0)

  useEffect(() => {
    idx.current = 0
    setDisplayed('')
    const interval = setInterval(() => {
      idx.current += 3
      if (idx.current >= text.length) {
        setDisplayed(text)
        clearInterval(interval)
      } else {
        setDisplayed(text.slice(0, idx.current))
      }
    }, speed)
    return () => clearInterval(interval)
  }, [text, speed])

  return <span>{displayed}<span className="animate-pulse">|</span></span>
}

export default function AssessmentTab() {
  const [patients, setPatients] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(-1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/patients')
      .then(r => r.json())
      .then(setPatients)
      .catch(() => {})
  }, [])

  const runAssessment = async () => {
    if (!selectedId) return
    setLoading(true)
    setError('')
    setResult(null)
    setCurrentStep(0)

    // Tick through the progress list while we wait for the API.
    const stepTimer = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= 3) { clearInterval(stepTimer); return prev }
        return prev + 1
      })
    }, 1500)

    try {
      const res = await fetch('/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_id: selectedId }),
      })
      clearInterval(stepTimer)
      setCurrentStep(4)

      if (!res.ok) throw new Error((await res.json()).detail || 'Assessment failed')
      const data = await res.json()

      setTimeout(() => {
        setResult(data)
        setLoading(false)
      }, 500)
    } catch (e) {
      clearInterval(stepTimer)
      setError(e.message)
      setLoading(false)
      setCurrentStep(-1)
    }
  }

  const risk = result ? RISK_STYLES[result.risk_level] || RISK_STYLES.LOW_RISK : null

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-2xl mx-auto">
        {/* Intro copy */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold tracking-tight mb-2">Patient Risk Assessment</h2>
          <p className="text-gray-500 text-sm">Assess patients against NICE NG12 cancer referral guidelines</p>
        </div>

        {/* Patient picker + run button */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl p-6 mb-6">
          <div className="flex gap-3">
            <select
              value={selectedId}
              onChange={e => setSelectedId(e.target.value)}
              className="flex-1 bg-[#0f0f0f] border border-[#333] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 appearance-none"
            >
              <option value="">Select a patient...</option>
              {patients.map(p => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.patient_id} — {p.name} ({p.age}{p.gender?.[0]}, {p.symptoms?.join(', ')})
                </option>
              ))}
            </select>
            <button
              onClick={runAssessment}
              disabled={!selectedId || loading}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-xl text-sm font-semibold transition-all hover:-translate-y-0.5 active:translate-y-0"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
              Assess
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl px-4 py-3 text-sm mb-6 animate-fade-up">
            <AlertTriangle size={14} className="inline mr-2" /> {error}
          </div>
        )}

        {/* Progress timeline during assessment */}
        {loading && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl p-6 mb-6 animate-fade-up">
            <div className="flex items-center gap-3 mb-5">
              <Loader2 size={20} className="animate-spin text-blue-400" />
              <span className="font-semibold text-sm">Analyzing patient against NG12 guidelines...</span>
            </div>
            <div className="space-y-3">
              {STEPS.map((step, i) => {
                const Icon = step.icon
                const isDone = currentStep > i
                const isActive = currentStep === i
                return (
                  <div key={i} className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                    isDone ? 'text-emerald-400' : isActive ? 'text-gray-300' : 'text-gray-600'
                  }`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border text-[10px] ${
                      isDone ? 'bg-emerald-500/10 border-emerald-500/40' :
                      isActive ? 'bg-blue-500/10 border-blue-500/40' :
                      'bg-[#0f0f0f] border-[#333]'
                    }`}>
                      {isDone ? '✓' : <Icon size={10} />}
                    </div>
                    <span>{step.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Completed assessment */}
        {result && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl overflow-hidden animate-fade-up">
            {/* Risk summary banner */}
            <div className="px-6 py-4 border-b border-[#333] flex items-center justify-between">
              <span className="font-semibold">{result.patient_name || result.patient_id}</span>
              <span className={`px-3 py-1 rounded-full text-[11px] font-bold font-mono tracking-wider border ${risk.bg} ${risk.text} ${risk.border}`}>
                {(result.risk_level || '').replace(/_/g, ' ')}
              </span>
            </div>

            <div className="p-6 space-y-5">
              {/* Recommended action */}
              <Section title="Recommended Action">
                <p className="text-sm text-gray-400 leading-relaxed">{result.recommended_action || 'N/A'}</p>
              </Section>

              {/* Potential cancer types */}
              {result.suspected_cancers?.length > 0 && (
                <Section title="Suspected Cancers">
                  <div className="flex flex-wrap gap-2">
                    {result.suspected_cancers.map((c, i) => (
                      <span key={i} className="bg-[#0f0f0f] border border-[#333] rounded-lg px-3 py-1 text-xs text-gray-400">
                        {c}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Model reasoning */}
              <Section title="Clinical Reasoning">
                <p className="text-sm text-gray-400 leading-relaxed">
                  <TypewriterText text={result.reasoning || 'N/A'} />
                </p>
              </Section>

              {/* Guideline citations */}
              {result.guideline_citations?.length > 0 && (
                <Section title="NG12 Citations">
                  <div className="space-y-2">
                    {result.guideline_citations.map((c, i) => (
                      <div key={i} className="bg-[#0f0f0f] border border-[#333] rounded-lg p-3 hover:border-blue-500/40 transition-colors">
                        <span className="font-mono text-xs font-semibold text-blue-400">
                          Rec {c.recommendation_id || 'N/A'}
                        </span>
                        {c.page && <span className="font-mono text-[10px] text-gray-600 ml-2">Page {c.page}</span>}
                        <p className="text-xs text-gray-500 mt-1 leading-relaxed">{c.text}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Extra notes */}
              {result.additional_notes && (
                <Section title="Additional Notes">
                  <p className="text-sm text-gray-400 leading-relaxed">{result.additional_notes}</p>
                </Section>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <h3 className="text-[10px] font-semibold font-mono text-gray-600 uppercase tracking-widest mb-2">{title}</h3>
      {children}
    </div>
  )
}
