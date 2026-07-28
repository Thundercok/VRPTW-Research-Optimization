import React, { useState, useEffect } from 'react';

export default function OnboardingTour() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [targetRect, setTargetRect] = useState(null);

  const steps = [
    {
      title: 'Welcome to NAMI Dispatch',
      description: 'Let us show you around the smart VRPTW optimization dashboard.',
      target: null
    },
    {
      title: 'Navigate between sections',
      description: 'Use the sidebar to switch between Dispatch, Fleet Management, Analytics, and Settings.',
      target: '.saas-sidebar'
    },
    {
      title: 'Choose a Solomon benchmark or import custom data',
      description: 'Select one of the classic VRPTW datasets or upload your own CSV/Excel file.',
      target: '#dataset-select'
    },
    {
      title: 'Run the AI optimization engine',
      description: 'Execute the hybrid DDQN-ALNS solver to find the optimal routes for your fleet.',
      target: '#run-model'
    },
    {
      title: 'AI Playground',
      description: 'Access AI tools and XAI console to manually polish and adjust your fleet routes.',
      target: '#btn-ai-playground'
    },
    {
      title: 'Settings',
      description: 'Customize your workspace preferences and view application status in the settings view.',
      target: '.nav-item[href="#settings"]'
    }
  ];

  const updateTargetRect = () => {
    const selector = steps[currentStep]?.target;
    if (selector) {
      const el = document.querySelector(selector);
      if (el) {
        setTargetRect(el.getBoundingClientRect());
      } else {
        setTargetRect(null);
      }
    } else {
      setTargetRect(null);
    }
  };

  useEffect(() => {
    const checkOnboarding = () => {
      const isComplete = localStorage.getItem('vrptw_onboarding_complete');
      if (!isComplete || isComplete === 'false') {
        setIsVisible(true);
        setCurrentStep(0);
      } else {
        setIsVisible(false);
      }
    };
    checkOnboarding();
    
    // Polling or listening to local storage to restart tour if requested from Settings
    window.addEventListener('storage', checkOnboarding);
    const interval = setInterval(checkOnboarding, 1000);
    return () => {
      window.removeEventListener('storage', checkOnboarding);
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (isVisible) {
      updateTargetRect();
      window.addEventListener('resize', updateTargetRect);
      return () => window.removeEventListener('resize', updateTargetRect);
    }
  }, [isVisible, currentStep]);

  const completeTour = () => {
    localStorage.setItem('vrptw_onboarding_complete', 'true');
    setIsVisible(false);
  };

  if (!isVisible) return null;

  const step = steps[currentStep];

  // If there's a target rect, we position a spotlight hole. 
  // We can achieve this with a box shadow spreading from a transparent div,
  // or simple masks. Let's use standard massive box shadow on an absolute div.

  const spotlightStyle = targetRect ? {
    position: 'absolute',
    top: targetRect.top - 8,
    left: targetRect.left - 8,
    width: targetRect.width + 16,
    height: targetRect.height + 16,
    borderRadius: '8px',
    boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.6)',
    pointerEvents: 'none',
    transition: 'all 0.3s ease-in-out'
  } : {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: 0,
    height: 0,
    boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.6)',
    pointerEvents: 'none',
    transition: 'all 0.3s ease-in-out'
  };

  const cardStyle = targetRect ? {
    position: 'absolute',
    top: targetRect.bottom + 20 > window.innerHeight - 200 ? targetRect.top - 220 : targetRect.bottom + 20,
    left: Math.max(20, Math.min(targetRect.left, window.innerWidth - 420)),
    transition: 'all 0.3s ease-in-out'
  } : {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    transition: 'all 0.3s ease-in-out'
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 10000, pointerEvents: 'auto', overflow: 'hidden' }}>
      <div style={spotlightStyle} />
      
      <div style={{
        ...cardStyle,
        background: 'var(--bg-surface)',
        padding: '24px',
        borderRadius: 'var(--r-lg)',
        width: '400px',
        boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
        border: '1px solid var(--border)',
        zIndex: 10001
      }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', color: 'var(--text-main)' }}>{step.title}</h3>
        <p style={{ margin: '0 0 24px 0', fontSize: '14px', color: 'var(--text-muted)', lineHeight: '1.5' }}>{step.description}</p>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            {steps.map((_, i) => (
              <div key={i} style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: i === currentStep ? 'var(--pine)' : 'var(--border-strong)',
                transition: 'background 0.3s'
              }} />
            ))}
          </div>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginRight: '8px' }}>
              {currentStep + 1}/{steps.length}
            </span>
            <button className="btn-secondary" onClick={completeTour}>Skip</button>
            <button className="btn-primary" onClick={() => {
              if (currentStep < steps.length - 1) {
                setCurrentStep(currentStep + 1);
              } else {
                completeTour();
              }
            }}>
              {currentStep < steps.length - 1 ? 'Next' : 'Done'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
