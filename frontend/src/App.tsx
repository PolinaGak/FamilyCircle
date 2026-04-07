// src/App.tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import LandingPage from './pages/landing/LandingPage';
import ProtectedRoute from './components/ProtectedRoute'; 
import VerifyPendingPage from './pages/auth/VerifyPendingPage';
import VerifyEmailPage from './pages/auth/VerifyEmailPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Главная страница для гостей */}
        <Route path="/" element={<LandingPage />} />

        {/* Страницы авторизации */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {/* ЗАЩИЩЕННЫЕ маршруты (только для авторизованных) */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<HomePage />} />
        </Route>

        {/* Резервный маршрут */}
        <Route path="*" element={<div>Страница не найдена</div>} />

        <Route path="/verify-pending" element={<VerifyPendingPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;