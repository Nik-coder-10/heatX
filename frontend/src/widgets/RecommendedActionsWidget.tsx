import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ClipboardList, Activity, Zap, Shield, Plus, RefreshCw } from 'lucide-react';

interface ActionItem {
  id: number;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  icon: React.ComponentType<{ className?: string }>;
  status: 'pending' | 'in-progress' | 'completed';
}

export default function RecommendedActionsWidget() {
  const [actions, setActions] = useState<ActionItem[]>([
    {
      id: 1,
      title: 'Expand Urban Green Spaces',
      description: 'Convert 5 vacant lots to pocket parks in heat-vulnerable neighborhoods.',
      priority: 'high',
      icon: Activity,
      status: 'pending',
    },
    {
      id: 2,
      title: 'Cool Roof Retrofit Program',
      description: 'Subsidize reflective roofing for 1000 residential buildings.',
      priority: 'high',
      icon: Zap,
      status: 'in-progress',
    },
    {
      id: 3,
      title: 'Heat Early Warning System',
      description: 'Deploy IoT sensors for real-time temperature monitoring.',
      priority: 'medium',
      icon: Shield,
      status: 'pending',
    },
    {
      id: 4,
      title: 'Public Awareness Campaign',
      description: 'Launch multilingual heat safety outreach in community centers.',
      priority: 'low',
      icon: ClipboardList,
      status: 'completed',
    },
  ]);

  const getPriorityColor = (priority: 'high' | 'medium' | 'low') => {
    switch (priority) {
      case 'high': return 'text-danger';
      case 'medium': return 'text-warning';
      case 'low': return 'text-success';
    }
  };

  const getStatusBadge = (status: 'pending' | 'in-progress' | 'completed'): { variant: 'warning' | 'info' | 'success', label: string } => {
    switch (status) {
      case 'pending': return { variant: 'warning', label: 'Pending' };
      case 'in-progress': return { variant: 'info', label: 'In Progress' };
      case 'completed': return { variant: 'success', label: 'Completed' };
    }
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Recommended Actions
          </h3>
          <Button variant="outline" size="sm" onClick={() => {
            // Simulate adding a new action
            const newAction: ActionItem = {
              id: Date.now(),
              title: 'New Action Item',
              description: 'Generated based on latest analysis',
              priority: 'medium',
              icon: Activity,
              status: 'pending',
            };
            setActions([...actions, newAction]);
          }}>
            <Plus className="h-4 w-4" /> Add Action
          </Button>
        </div>

        <div className="space-y-4">
          {actions.map((action) => (
            <div key={action.id} className="flex items-start space-x-3 p-3 rounded-lg bg-background/50 dark:bg-background-dark/50">
              <div className="flex-shrink-0">
                <action.icon className={`h-5 w-5 ${getPriorityColor(action.priority)}`} />
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex justify-between">
                  <h4 className="font-semibold text-text-primary dark:text-text-primary-dark">
                    {action.title}
                  </h4>
                  <Badge variant={getPriorityColor(action.priority).includes('danger') ? 'danger' : getPriorityColor(action.priority).includes('warning') ? 'warning' : 'success'}>
                    {action.priority.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-sm text-text-secondary line-clamp-2">
                  {action.description}
                </p>
                <div className="flex items-center space-x-2 text-xs">
                  <span className="font-medium">Status: </span>
                  <Badge
                    variant={getStatusBadge(action.status).variant}
                    className="text-xs"
                  >
                    {getStatusBadge(action.status).label}
                  </Badge>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex justify-between">
            <Button variant="outline" size="sm" onClick={() => {
              // Simulate updating progress
              const updatedActions = actions.map(action => {
                if (action.status === 'pending' && Math.random() > 0.7) {
                  return { ...action, status: 'in-progress' as const };
                }
                if (action.status === 'in-progress' && Math.random() > 0.5) {
                  return { ...action, status: 'completed' as const };
                }
                return action;
              });
              setActions(updatedActions);
            }}>
              <RefreshCw className="h-4 w-4" />
              Update Progress
            </Button>
            <span className="text-xs text-text-secondary">
              {actions.filter(a => a.status === 'completed').length}/{actions.length} completed
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}