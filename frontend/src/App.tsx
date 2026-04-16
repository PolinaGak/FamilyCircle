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
import JoinFamilyPage from './pages/JoinFamilyPage';
import SettingsPage from './pages/SettingsPage';
import EditProfilePage from './pages/EditProfilePage';

import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Публичные маршруты*/}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/verify-pending" element={<VerifyPendingPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Защищенные маршруты*/}
        <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<HomePage />} />
          <Route path="/family/:id" element={<FamilyPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/join-family" element={<JoinFamilyPage />} />
          <Route path="/tree" element={<div>Семейное древо</div>} />
          <Route path="/chat" element={<div>Чат</div>} />
          <Route path="/gallery" element={<div>Галерея</div>} />
          <Route path="/calendar" element={<div>Календарь</div>} />
          <Route path="/edit-profile" element={<EditProfilePage />} />
        </Route>

        {/* Резервный маршрут */}
        <Route path="*" element={<div>Страница не найдена</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;