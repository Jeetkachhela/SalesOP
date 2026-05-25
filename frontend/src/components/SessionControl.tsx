"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/store/useAuth";
import { toast } from "sonner";
import { Clock, ShieldAlert } from "lucide-react";

const INACTIVITY_TIMEOUT = 10 * 60 * 1000; // 10 minutes
const WARNING_TIMEOUT = 9 * 60 * 1000; // Warn after 9 minutes (1 minute remaining)

export default function SessionControl() {
  const { token, logout } = useAuth();
  const [isWarningActive, setIsWarningActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(60); // 60 seconds countdown
  
  const lastActivityRef = useRef<number>(Date.now());
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const warningToastIdRef = useRef<string | number | null>(null);

  const resetTimer = () => {
    lastActivityRef.current = Date.now();
    
    // If the warning toast was active, dismiss it and reset warning state
    if (isWarningActive) {
      setIsWarningActive(false);
      if (warningToastIdRef.current) {
        toast.dismiss(warningToastIdRef.current);
        warningToastIdRef.current = null;
      }
      toast.success("Session extended successfully", { duration: 2000 });
    }
  };

  useEffect(() => {
    if (!token) return;

    // Track active interactions
    const events = ["mousemove", "keydown", "mousedown", "scroll", "click", "touchstart"];
    
    const activityHandler = () => resetTimer();
    
    events.forEach(event => {
      window.addEventListener(event, activityHandler, { passive: true });
    });

    // Check inactivity status every 1 second
    timerIntervalRef.current = setInterval(() => {
      const inactiveDuration = Date.now() - lastActivityRef.current;

      if (inactiveDuration >= INACTIVITY_TIMEOUT) {
        // Log out immediately
        clearInterval(timerIntervalRef.current!);
        if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
        if (warningToastIdRef.current) toast.dismiss(warningToastIdRef.current);
        
        logout();
        toast.error("You have been logged out due to inactivity.", {
          duration: 8000,
          icon: <ShieldAlert className="text-rose-500" />,
        });
      } else if (inactiveDuration >= WARNING_TIMEOUT && !isWarningActive) {
        // Start countdown and show warning toast
        setIsWarningActive(true);
        const remainingSeconds = Math.ceil((INACTIVITY_TIMEOUT - inactiveDuration) / 1000);
        setTimeLeft(remainingSeconds);
      }
    }, 1000);

    return () => {
      events.forEach(event => {
        window.removeEventListener(event, activityHandler);
      });
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [token, isWarningActive]);

  // Handle countdown updates
  useEffect(() => {
    if (isWarningActive && token) {
      // Show Sonner warning toast with a custom countdown UI
      warningToastIdRef.current = toast.warning(
        `Session Expiring: Inactive for ${Math.floor(WARNING_TIMEOUT / 60000)} minutes. You will be logged out in ${timeLeft}s. Move mouse or press any key to extend session.`,
        {
          duration: Infinity, // Keep open until manual close or action
          id: "session-warning",
          icon: <Clock className="text-amber-500 animate-pulse" />,
        }
      );

      countdownIntervalRef.current = setInterval(() => {
        const inactiveDuration = Date.now() - lastActivityRef.current;
        const secondsLeft = Math.max(0, Math.ceil((INACTIVITY_TIMEOUT - inactiveDuration) / 1000));
        
        setTimeLeft(secondsLeft);
        
        if (secondsLeft <= 0) {
          clearInterval(countdownIntervalRef.current!);
        } else {
          // Update toast message dynamically
          toast.warning(
            `Session Expiring: You will be logged out in ${secondsLeft} seconds due to inactivity. Move mouse or press any key to extend.`,
            {
              id: "session-warning",
              icon: <Clock className="text-amber-500 animate-pulse" />,
            }
          );
        }
      }, 1000);
    }

    return () => {
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [isWarningActive, timeLeft, token]);

  return null;
}
