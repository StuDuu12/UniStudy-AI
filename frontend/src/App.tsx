import { AppShell } from './components/layout/AppShell';
import { useChat } from './hooks/useChat';

export function App() {
  const chat = useChat();

  return <AppShell {...chat} />;
}

export default App;
