import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const userRole = localStorage.getItem("userRole"); // Get user role from localStorage

  //const username = "Guest"; // Placeholder for username

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    
    /*<div className="navbar-container">
      <div className="welcome-guest">
        Welcome, {username}
      </div>*/
      <div className="hamburger-menu">
        <input
          type="checkbox"
          id="menu-toggle"
          checked={isMenuOpen}
          onChange={toggleMenu}
          style={{ display: 'none' }} // Hide the default checkbox
        />
        <label htmlFor="menu-toggle" className="menu-icon">
          {isMenuOpen ? 'X' : '☰'} {/* Change icon when open */}
        </label>

        {isMenuOpen && (
          <nav className="sidebar">
            <button className="hm-close-button" onClick={toggleMenu}>
              x
            </button>
            <ul>
              <li><Link to="/home" onClick={toggleMenu}>Home</Link></li>
              <li><Link to="/analysis" onClick={toggleMenu}>Analysis Tool</Link></li>
              <li><Link to="/settings" onClick={toggleMenu}>Settings</Link></li>
              <li><Link to="/users" onClick={toggleMenu}>Users</Link></li>
            </ul>
          </nav>
        )}
      </div>
    //</div>
  );
}
// uncomment below and replace for the above statement so it shows on
// the Navbar what you can and cant do based off the role

/*</*div className="hamburger-menu">
<input
  type="checkbox"
  id="menu-toggle"
  checked={isMenuOpen}
  onChange={toggleMenu}
  style={{ display: 'none' }} // Hide the default checkbox
/>
<label htmlFor="menu-toggle" className="menu-icon">
  {isMenuOpen ? 'X' : '☰'} {/* Change icon when open *//*}
</label>

{isMenuOpen && (
  <nav className="sidebar">
    <button className="hm-close-button" onClick={toggleMenu}>
      x
    </button>
    <ul>
      <li><Link to="/home" onClick={toggleMenu}>Home</Link></li>
      <li><Link to="/analysis" onClick={toggleMenu}>Analysis Tool</Link></li>

      {/* Conditional rendering based on role *//*}
      {userRole === "admin" && (
        <>
          <li><Link to="/settings" onClick={toggleMenu}>Settings</Link></li>
          <li><Link to="/users" onClick={toggleMenu}>Manage Users</Link></li>
        </>
      )}

      {userRole === "operator" && (
        <li><Link to="/settings" onClick={toggleMenu}>Settings</Link></li>
      )}

      {/* No link for observer role for settings or user management *//*}
    </ul>
  </nav>
)}
</div>
);
}*/

export default Navbar;