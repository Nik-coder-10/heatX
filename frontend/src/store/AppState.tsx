import { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { UploadedFile, AppState } from '@/types';

type Action =
  | { type: 'ADD_FILE'; file: UploadedFile }
  | { type: 'REMOVE_FILE'; id: string }
  | { type: 'RENAME_FILE'; id: string; name: string }
  | { type: 'SELECT_FILE'; id: string | null }
  | { type: 'SET_LOCATION'; location: AppState['selectedLocation'] }
  | { type: 'CLEAR_FILES' };

const initialState: AppState = {
  uploadedFiles: [],
  selectedFileId: null,
  selectedLocation: null,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'ADD_FILE':
      return { ...state, uploadedFiles: [...state.uploadedFiles, action.file] };
    case 'REMOVE_FILE':
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.filter((f) => f.id !== action.id),
        selectedFileId: state.selectedFileId === action.id ? null : state.selectedFileId,
      };
    case 'RENAME_FILE':
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.map((f) =>
          f.id === action.id ? { ...f, name: action.name } : f
        ),
      };
    case 'SELECT_FILE':
      return { ...state, selectedFileId: action.id };
    case 'SET_LOCATION':
      return { ...state, selectedLocation: action.location };
    case 'CLEAR_FILES':
      return { ...state, uploadedFiles: [], selectedFileId: null };
    default:
      return state;
  }
}

const AppStateContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<Action>;
}>({ state: initialState, dispatch: () => {} });

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppStateContext.Provider value={{ state, dispatch }}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
