"use client"

import React, { useState, useEffect } from 'react';
import { LoginPage } from './components/LoginPage';
import { useRouter } from 'next/navigation';

export default function MonopolyBoss() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 1. Wrap the navigation in useEffect
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/monopoly');
    }
  }, [isAuthenticated, router]);

  const handleLogin = (id: string) => {
    // setUserId(id);
    setIsLoading(true); // Start loading
    
    setTimeout(() => {
      setIsAuthenticated(true);
      setIsLoading(false); // Stop loading only after the 1.5s delay
    }, 1500);
  };

  // 2. Only return the Login UI if not authenticated
  if (!isAuthenticated) {
    return (
      <LoginPage 
        onLogin={handleLogin}
        isLoading={isLoading}
      />
    );
  }

  // 3. Return null or a loading spinner while the useEffect handles the redirect
  return null; 
}