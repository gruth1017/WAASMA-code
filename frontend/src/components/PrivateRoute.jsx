import { Navigate } from 'react-router-dom';

const PrivateRoute = ({ children }) => {
  const user = JSON.parse(localStorage.getItem('user')); // or use context
  const token = localStorage.getItem('authToken'); // Use the key you've chosen

  if (!user) {
    return <Navigate to="/" />; // redirect to login
  }

  return children; // let them in
};

export default PrivateRoute;