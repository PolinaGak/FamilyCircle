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
import FamilyPage from './pages/FamilyPage';
import JoinFamilyPage from './pages/JoinFamilyPage';  // ← ДОБАВИТЬ
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Публичные маршруты */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/verify-pending" element={<VerifyPendingPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Защищенные маршруты */}
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

        <Route 
          path="/family/:id" 
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<FamilyPage />} />
        </Route>

        {/*присоединение к семье*/}
        <Route 
          path="/join-family" 
          element={
            <ProtectedRoute>
              <JoinFamilyPage />
            </ProtectedRoute>
          }
        />

        {/* Резервный маршрут */}
        <Route path="*" element={<div>Страница не найдена</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;