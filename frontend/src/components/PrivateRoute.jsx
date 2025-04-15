import React from "react";
import { Navigate } from "react-router-dom";

// Wrap routes with this to restrict access based on user role
const PrivateRoute = ({ children, allowedRoles }) => {
  // Get role from localStorage (set at login)
  const userRole = localStorage.getItem("userRole");

  if (!userRole) {
    // If no role found, user isn't logged in — redirect to login
    return <Navigate to="/" />;
  }

  if (allowedRoles && !allowedRoles.includes(userRole)) {
    // If role is not in allowed list, redirect to unauthorized page
    return <Navigate to="/unauthorized" />;
  }

  // Otherwise, allow the route to render
  return children;
};

export default PrivateRoute;
