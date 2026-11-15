import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Origin from './pages/Origin';
import Mathematics from './pages/Mathematics';
import Explorer from './pages/Explorer';
import LetterDetail from './pages/LetterDetail';
import Lab from './pages/Lab';
import Simulator from './pages/Simulator';
import System from './pages/System';
import Research from './pages/Research';
import Documentation from './pages/Documentation';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/origin" element={<Origin />} />
        <Route path="/origin/:section" element={<Origin />} />
        <Route path="/mathematics" element={<Mathematics />} />
        <Route path="/mathematics/:section" element={<Mathematics />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/explorer/letter/:letter" element={<LetterDetail />} />
        <Route path="/explorer/:letter" element={<LetterDetail />} />
        <Route path="/laboratory" element={<Lab />} />
        <Route path="/laboratory/:op" element={<Lab />} />
        <Route path="/lab" element={<Lab />} />
        <Route path="/computing" element={<System />} />
        <Route path="/computing/:section" element={<System />} />
        <Route path="/system" element={<System />} />
        <Route path="/simulator" element={<Simulator />} />
        <Route path="/research" element={<Research />} />
        <Route path="/research/:section" element={<Research />} />
        <Route path="/documentation" element={<Documentation />} />
        <Route path="/documentation/:section" element={<Documentation />} />
        <Route path="/docs" element={<Documentation />} />
      </Routes>
    </Layout>
  );
}
