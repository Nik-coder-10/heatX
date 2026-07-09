import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center p-12 text-center min-h-[400px]">
          <div className="w-12 h-12 rounded-xl bg-danger/10 flex items-center justify-center mb-4">
            <AlertTriangle className="h-6 w-6 text-danger" />
          </div>
          <h2 className="text-sm font-semibold text-text-primary mb-1">Something went wrong</h2>
          <p className="text-xs text-text-secondary mb-4 max-w-md">
            {this.state.error.message || 'An unexpected error occurred'}
          </p>
          <Button variant="outline" size="sm" onClick={() => this.setState({ error: null })}>
            Try Again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
