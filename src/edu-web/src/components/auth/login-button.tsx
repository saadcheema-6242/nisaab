import { LogIn } from 'lucide-react'
import { useSearch } from '@tanstack/react-router'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export const LoginButton = () => {
  const {
    login,
    sendPasswordReset,
    isLoading,
    loginError,
    passwordResetError,
    passwordResetSent,
  } = useAuth()
  const search = useSearch({ from: '/' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    // Store the redirect URL before login
    if (search?.redirect) {
      sessionStorage.setItem('auth.redirect', search.redirect)
    }
    login({ email, password })
  }

  const handlePasswordReset = () => {
    sendPasswordReset(email)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2">
          <LogIn className="h-4 w-4" />
          Sign in
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sign in</DialogTitle>
          <DialogDescription>
            Sign in with your email and password.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
          {(loginError || passwordResetError) && (
            <p className="text-sm text-red-500">
              {loginError instanceof Error
                ? loginError.message
                : passwordResetError instanceof Error
                  ? passwordResetError.message
                  : 'Login failed'}
            </p>
          )}
          {passwordResetSent && (
            <p className="text-sm text-muted-foreground">
              Password reset email sent to {email}.
            </p>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={isLoading || !email}>
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handlePasswordReset}
              disabled={isLoading || !email}
            >
              Forgot password
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
