import { StatusBar } from 'expo-status-bar';
import RootNavigator from './src/navigation/Root';

export default function App() {
  return (
    <>
      <RootNavigator />
      <StatusBar style="auto" />
    </>
  );
}
