"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BrainCircuit, LogOut } from "lucide-react";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userName, setUserName] = useState("");

  // Check auth status on load and when the route changes
  useEffect(() => {
    const token = localStorage.getItem("token");
    const name = localStorage.getItem("userName");
    setIsAuthenticated(!!token);
    if (name) setUserName(name);
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    setIsAuthenticated(false);
    router.push("/");
  };

  return (
    <nav className="sticky top-0 w-full bg-white/80 backdrop-blur-md border-b border-gray-100 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo / Brand */}
        <Link
          href="/"
          className="flex items-center gap-2 text-blue-600 hover:opacity-80 transition"
        >
          <BrainCircuit className="w-6 h-6" />
          <span className="font-bold text-lg tracking-tight">MindFlow</span>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
          >
            Home
          </Link>
          <Link
            href="#"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
          >
            About Us
          </Link>

          {isAuthenticated ? (
            <div className="flex items-center gap-4 ml-4 pl-4 border-l border-gray-200">
              <span className="text-sm font-medium text-gray-900">
                Hi, {userName}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-sm font-medium text-red-600 hover:text-red-700 transition"
              >
                <LogOut className="w-4 h-4" /> Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 ml-4 pl-4 border-l border-gray-200">
              <Link
                href="/login"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition"
              >
                Login
              </Link>
              <Link
                href="/signup"
                className="text-sm font-medium bg-blue-600 text-white px-4 py-2 rounded-full hover:bg-blue-700 transition shadow-sm"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
