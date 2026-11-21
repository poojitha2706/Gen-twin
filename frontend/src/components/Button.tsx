import type { ButtonHTMLAttributes } from 'react'

const variants = {
  primary: 'bg-accent text-background hover:opacity-90',
  secondary: 'border border-line bg-raised text-fg hover:bg-line/40',
  ghost: 'text-fg hover:bg-line/50',
  danger: 'bg-critical text-background hover:opacity-90',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants
  size?: 'sm' | 'md'
}

export function Button({ variant = 'secondary', size = 'md', className = '', ...rest }: Props) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-2 rounded-control font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
        size === 'sm' ? 'h-8 px-3 text-sm' : 'h-9 px-4 text-base'
      } ${variants[variant]} ${className}`}
    />
  )
}
