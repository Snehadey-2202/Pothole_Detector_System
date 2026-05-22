import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { 
  RefreshCw, 
  Trash2, 
  Camera, 
  MapPin, 
  Activity, 
  ShieldAlert, 
  Cpu, 
  TrendingUp, 
  Zap, 
  Compass, 
  Award
} from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// Custom Map Controller to pan and fly to selected detection
function ChangeMapView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, zoom, { animate: true, duration: 1.0 });
    }
  }, [center, zoom, map]);
  return null;
}

// Background image preloader component to prevent flickering
function SmoothImage({ src, alt, className, onError }) {
  const [currentSrc, setCurrentSrc] = useState(src);
  const onErrorRef = useRef(onError);
  const isPreloading = currentSrc !== src;

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (src === currentSrc) return undefined;

    const img = new Image();
    img.src = src;
    img.onload = () => {
      setCurrentSrc(src);
    };
    img.onerror = () => {
      if (onErrorRef.current) onErrorRef.current();
    };
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src, currentSrc]);

  return (
    <div className="relative w-full h-full overflow-hidden flex items-center justify-center">
      <img 
        src={currentSrc} 
        alt={alt} 
        className={`${className} transition-all duration-500 ease-in-out ${isPreloading ? 'scale-[0.98] opacity-75 blur-[1px]' : 'scale-100 opacity-100'}`}
      />
      {isPreloading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/20 backdrop-blur-[1px] transition-opacity duration-300">
          <div className="flex flex-col items-center gap-2">
            <RefreshCw className="w-5 h-5 text-primary animate-spin" />
            <span className="text-[9px] text-primary font-mono tracking-widest uppercase animate-pulse">Preloading...</span>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState({ total_detected: 0 });
  const [timestamp, setTimestamp] = useState(0);
  const [chartData, setChartData] = useState([]);
  const [mapCenter, setMapCenter] = useState([37.7749, -122.4194]);
  const [mapZoom, setMapZoom] = useState(13);
  const [selectedDetId, setSelectedDetId] = useState(null);
  
  // Page-Level Tabs state: 'detection' (Live Feed & Anomaly Detection) or 'analytics' (Confidence Graph & Analytics)
  const [activeTab, setActiveTab] = useState('detection');

  const fetchData = useCallback(async () => {
    try {
      const [detRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/detections`),
        axios.get(`${API_BASE_URL}/api/stats`)
      ]);
      setDetections(detRes.data);
      setStats(statsRes.data);
      
      // Update chart data (group by minute or just show last 12)
      const recent = [...detRes.data].reverse().slice(-12);
      const formattedChart = recent.map((d) => ({
        time: new Date(d.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'}),
        confidence: Math.round(d.confidence * 100)
      }));
      setChartData(formattedChart);

      // Default center map to latest detection if available and not yet set
      if (detRes.data.length > 0 && selectedDetId === null) {
        const latest = detRes.data[0];
        setMapCenter([latest.latitude, latest.longitude]);
      }

    } catch (err) {
      console.error("Error fetching data:", err);
    }
  }, [selectedDetId]);

  const handleReset = async () => {
    if (window.confirm("Are you sure you want to clear all telemetry detections?")) {
      try {
        await axios.post(`${API_BASE_URL}/api/reset`);
        setDetections([]);
        setStats({ total_detected: 0 });
        setChartData([]);
        setSelectedDetId(null);
        setMapCenter([37.7749, -122.4194]);
        setMapZoom(13);
      } catch (err) {
        console.error("Failed to reset DB", err);
      }
    }
  };

  const handleLogClick = (det) => {
    setSelectedDetId(det.id);
    setMapCenter([det.latitude, det.longitude]);
    setMapZoom(17); // Close fly-in zoom
  };

  useEffect(() => {
    const refresh = () => {
      fetchData();
      setTimestamp(Date.now()); // force image reload
    };

    const initialRefresh = setTimeout(refresh, 0);
    // Poll every 3 seconds for new detections and to refresh the live camera feed
    const interval = setInterval(refresh, 3000);
    return () => {
      clearTimeout(initialRefresh);
      clearInterval(interval);
    };
  }, [fetchData]);

  // Generate glowing HTML custom Leaflet markers relative to detection confidence
  const createGlowingMarker = (confidence) => {
    const scale = 0.85 + confidence * 0.45;
    return L.divIcon({
      className: 'custom-glow-marker',
      html: `
        <div class="marker-pulse-ring" style="transform: scale(${scale});"></div>
        <div class="marker-core"></div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  // Derived Analytics Stats
  const runningAvgConf = detections.length > 0
    ? (detections.reduce((acc, curr) => acc + curr.confidence, 0) / detections.length * 100).toFixed(0)
    : 0;

  const peakConf = detections.length > 0
    ? (Math.max(...detections.map(d => d.confidence)) * 100).toFixed(0)
    : 0;

  const highRiskCount = detections.filter(d => d.confidence > 0.85).length;
  const medRiskCount = detections.filter(d => d.confidence <= 0.85).length;
  
  const highRiskPct = detections.length > 0
    ? ((highRiskCount / detections.length) * 100).toFixed(0)
    : 0;
  const medRiskPct = detections.length > 0
    ? ((medRiskCount / detections.length) * 100).toFixed(0)
    : 0;

  return (
    <div className="min-h-screen bg-background text-text flex flex-col font-sans overflow-x-hidden antialiased">
      {/* Premium Glassmorphic Header */}
      <header className="glass-header py-4 px-6 shadow-xl flex flex-col sm:flex-row justify-between items-center z-[1001] gap-4 relative">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center border border-primary/45 shadow-lg shadow-primary/5">
            <Cpu className="text-primary w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl lg:text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-primary via-indigo-400 to-accent tracking-tight">
              Pothole Detector AI
            </h1>
            <p className="text-[10px] text-muted font-mono tracking-widest uppercase flex items-center gap-1.5">
              <span>Edge Telemetry Hub</span>
              <span className="w-1 h-1 bg-muted rounded-full"></span>
              <span className="text-primary font-bold">NODE_01</span>
            </p>
          </div>
        </div>
        
        {/* Statistics and Status Controls */}
        <div className="flex flex-wrap items-center justify-center gap-4">
          {/* Active Status Badge */}
          <div className="flex items-center gap-2 bg-slate-950/60 border border-slate-800/80 px-3.5 py-1.5 rounded-full shadow-inner">
            <span className="heartbeat-status">
              <span className="heartbeat-pulse bg-emerald-500"></span>
              <span className="heartbeat-dot bg-emerald-400"></span>
            </span>
            <span className="text-[9px] font-mono font-bold tracking-widest text-emerald-400">LIVE FEED ACTIVE</span>
          </div>

          {/* Anomaly Count Mini Card */}
          <div className="bg-slate-950/60 rounded-xl px-4 py-1 border border-slate-800/80 shadow-lg flex flex-col">
            <span className="text-muted text-[8px] uppercase tracking-widest font-black">Total Anomalies</span>
            <span className="text-base font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-accent to-pink-500 font-mono leading-tight">
              {stats.total_detected}
            </span>
          </div>

          {/* Avg Confidence Mini Card */}
          <div className="bg-slate-950/60 rounded-xl px-4 py-1 border border-slate-800/80 shadow-lg flex flex-col">
            <span className="text-muted text-[8px] uppercase tracking-widest font-black">Avg Confidence</span>
            <span className="text-base font-extrabold text-primary font-mono leading-tight">
              {runningAvgConf}%
            </span>
          </div>

          {/* Reset / Purge Action */}
          <button 
            onClick={handleReset}
            className="flex items-center gap-2 bg-accent/10 hover:bg-accent/20 text-accent border border-accent/30 px-3.5 py-2 rounded-xl transition-all active:scale-95 text-xs font-bold shadow-md shadow-accent/5"
            title="Clear all detections from database"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Purge Data</span>
          </button>
        </div>
      </header>

      {/* Page-Level Glassmorphic Navigation Tabs */}
      <div className="px-4 lg:px-6 pt-6 max-w-[1700px] mx-auto w-full">
        <div className="flex gap-2 p-1.5 bg-slate-950/45 backdrop-blur-md rounded-2xl border border-white/5 shadow-xl relative">
          <button
            onClick={() => setActiveTab('detection')}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl transition-all duration-300 font-sans text-xs sm:text-sm font-bold ${
              activeTab === 'detection'
                ? 'bg-primary/20 text-text border border-primary/30 shadow-lg shadow-primary/5'
                : 'text-muted hover:text-slate-200 hover:bg-white/5 border border-transparent'
            }`}
          >
            <Camera className={`w-4 h-4 ${activeTab === 'detection' ? 'animate-pulse text-primary' : ''}`} />
            <span>Live Feed & Anomaly Detection</span>
          </button>
          
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl transition-all duration-300 font-sans text-xs sm:text-sm font-bold ${
              activeTab === 'analytics'
                ? 'bg-primary/20 text-text border border-primary/30 shadow-lg shadow-primary/5'
                : 'text-muted hover:text-slate-200 hover:bg-white/5 border border-transparent'
            }`}
          >
            <Activity className={`w-4 h-4 ${activeTab === 'analytics' ? 'text-accent' : ''}`} />
            <span>Confidence Graph & Analytics</span>
          </button>
        </div>
      </div>

      {/* Main View Grid - fully responsive and height stabilized */}
      <main className="flex-grow p-4 lg:p-6 grid grid-cols-1 gap-6 max-w-[1700px] mx-auto w-full lg:h-[calc(100vh-164px)] h-auto overflow-hidden">
        
        {activeTab === 'detection' ? (
          /* TAB 1: LIVE FEED & ANOMALY DETECTION (3 Column Layout) */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full w-full animate-fade-in">
            
            {/* Left Column: Camera Live Feed */}
            <div className="lg:col-span-3 glass-panel rounded-2xl flex flex-col lg:h-full h-[390px] overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-slate-950/45 flex items-center justify-between">
                <h2 className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-2">
                  <Camera className="w-3.5 h-3.5 text-primary" /> Live Cam Feed
                </h2>
                <span className="text-[9px] font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 animate-pulse">
                  ONLINE
                </span>
              </div>
              
              <div className="flex-grow p-4 flex flex-col justify-between gap-4 min-h-0">
                <div className="flex-grow relative bg-slate-950 flex items-center justify-center p-1.5 rounded-xl border border-white/5 h-[190px] lg:h-auto min-h-0 overflow-hidden shadow-inner">
                  <SmoothImage 
                    src={`${API_BASE_URL}/detections/current_frame.jpg?t=${timestamp}`}
                    alt="Live stream feed"
                    className="w-full h-full object-cover rounded-lg"
                    onError={() => {}}
                  />
                  <div className="absolute bottom-3 right-3 bg-slate-950/80 px-2 py-1 rounded text-[8px] font-mono text-white/60 border border-white/5 backdrop-blur-sm tracking-wider">
                    FPS: 1.0 | 720p
                  </div>
                </div>

                {/* Telemetry Status Summary Card */}
                <div className="bg-slate-950/40 rounded-xl p-3 border border-white/5 space-y-1.5 text-[10px] font-mono">
                  <div className="flex justify-between items-center text-muted">
                    <span>Active Camera ID</span>
                    <span className="text-slate-200 font-bold">CAM_01_EDGE</span>
                  </div>
                  <div className="flex justify-between items-center text-muted">
                    <span>Latency</span>
                    <span className="text-primary font-bold">~42ms</span>
                  </div>
                  <div className="flex justify-between items-center text-muted">
                    <span>Processing Node</span>
                    <span className="text-accent font-bold">EDGE_AI_01</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Center Column: Interactive Detection Map */}
            <div className="lg:col-span-6 glass-panel rounded-2xl overflow-hidden relative lg:h-full h-[450px] min-h-[350px]">
              <div className="absolute top-4 right-4 z-[1000] bg-slate-950/85 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-white/5 shadow-2xl flex items-center gap-2">
                 <MapPin className="w-3.5 h-3.5 text-accent animate-bounce" />
                 <h2 className="font-extrabold text-slate-100 text-xs tracking-wider uppercase font-mono">Detection Map</h2>
              </div>
              
              <MapContainer 
                center={mapCenter} 
                zoom={mapZoom} 
                style={{ height: '100%', width: '100%', position: 'absolute', top: 0, left: 0 }}
                className="z-0"
              >
                <ChangeMapView center={mapCenter} zoom={mapZoom} />
                <TileLayer
                  attribution='&copy; OpenStreetMap'
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />
                {detections.map((det) => (
                  <Marker 
                    key={det.id} 
                    position={[det.latitude, det.longitude]}
                    icon={createGlowingMarker(det.confidence)}
                  >
                    <Popup className="custom-popup">
                      <div className="w-48 flex flex-col gap-2 p-1.5 text-text">
                        <div className="relative rounded-lg overflow-hidden border border-white/5 shadow-inner bg-black/40 h-28">
                          <img 
                            src={`${API_BASE_URL}${det.image_path}`} 
                            alt="Pothole detection" 
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="bg-slate-950/60 rounded-lg p-2 border border-white/5 text-[10px] space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="text-muted">Confidence</span>
                            <span className="font-bold text-accent font-mono text-xs">
                              {(det.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-muted">Coords</span>
                            <span className="font-mono text-[9px]">
                              {det.latitude.toFixed(4)}, {det.longitude.toFixed(4)}
                            </span>
                          </div>
                          <div className="pt-1 mt-1 border-t border-white/5 text-[8px] text-muted font-mono">
                            {new Date(det.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>

            {/* Right Column: Incident Feed */}
            <div className="lg:col-span-3 glass-panel rounded-2xl flex flex-col lg:h-full h-[500px] overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-slate-950/45 flex items-center justify-between">
                <div>
                  <h2 className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-2">
                    <ShieldAlert className="w-3.5 h-3.5 text-accent animate-pulse" /> Incident Feed
                  </h2>
                  <p className="text-[9px] text-muted mt-0.5">Real-time edge telemetry logs</p>
                </div>
                <span className="text-[10px] font-mono font-bold bg-white/5 border border-white/5 px-2.5 py-0.5 rounded-full text-slate-300">
                  {detections.length} logs
                </span>
              </div>

              {/* Enhanced Scrollable list container with shadows */}
              <div className="flex-grow relative min-h-0 bg-slate-950/10">
                <div className="absolute top-0 left-0 right-0 h-4 bg-gradient-to-b from-[#090d16]/30 to-transparent pointer-events-none z-10" />
                <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[#090d16]/50 to-transparent pointer-events-none z-10" />

                <div className="w-full h-full overflow-y-auto p-4 space-y-3 custom-scrollbar pr-2">
                  {detections.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-muted/65 text-center p-4">
                      <RefreshCw className="w-8 h-8 mb-2 animate-spin text-primary/40" />
                      <p className="text-xs font-semibold tracking-wider font-mono uppercase">Awaiting Stream Anomalies...</p>
                      <p className="text-[10px] text-muted/50 mt-1 font-mono">Simulate a pothole on the edge device to trigger logs</p>
                    </div>
                  ) : (
                    detections.map((det) => {
                      const isSelected = selectedDetId === det.id;
                      return (
                        <div 
                          key={det.id} 
                          onClick={() => handleLogClick(det)}
                          className={`rounded-xl p-3 border cursor-pointer flex gap-3 transition-all duration-300 group hover:scale-[1.01] ${
                            isSelected 
                              ? 'bg-primary/10 border-primary shadow-lg shadow-primary/5' 
                              : 'bg-slate-950/30 border-white/5 hover:border-primary/40 hover:bg-slate-950/50'
                          }`}
                        >
                          <div className="relative flex-shrink-0">
                            <img 
                              src={`${API_BASE_URL}${det.image_path}`} 
                              alt="pothole thumbnail" 
                              className={`w-14 h-14 object-cover rounded-lg border transition-all duration-300 ${
                                isSelected ? 'border-primary' : 'border-white/5 group-hover:border-primary/30'
                              }`}
                            />
                            <div className="absolute -bottom-1.5 -right-1.5 bg-slate-950 border border-white/10 rounded-full px-1 py-0.2 flex items-center justify-center text-[8px] font-bold text-accent font-mono shadow-md">
                              {(det.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="flex-grow flex flex-col justify-between min-w-0">
                            <div className="flex justify-between items-start">
                              <span className="text-[11px] font-bold text-slate-100 truncate group-hover:text-primary transition-colors">
                                Pothole Anomaly
                              </span>
                              <span className="text-[8px] text-muted font-mono leading-none">
                                {new Date(det.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                              </span>
                            </div>
                            
                            <div className="text-[9px] text-muted font-mono truncate flex items-center gap-1 mt-1">
                              <MapPin className="w-2.5 h-2.5 text-primary flex-shrink-0" />
                              <span className="truncate">{det.latitude.toFixed(4)}, {det.longitude.toFixed(4)}</span>
                            </div>
                            
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${det.confidence > 0.85 ? 'bg-red-500' : 'bg-amber-500'}`}></span>
                              <span className="text-[8px] text-muted uppercase font-mono tracking-widest">
                                {det.confidence > 0.85 ? 'High Risk' : 'Medium Risk'}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

          </div>
        ) : (
          /* TAB 2: CONFIDENCE GRAPH & ANALYTICS (Analytics Command Deck with Map integrated!) */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full w-full animate-fade-in">
            
            {/* Left Column: Trend Graph (col-span-5) */}
            <div className="lg:col-span-5 glass-panel rounded-2xl flex flex-col lg:h-full h-[450px] overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-slate-950/45 flex items-center justify-between">
                <div>
                  <h2 className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-2">
                    <TrendingUp className="w-3.5 h-3.5 text-primary" /> Confidence Trend Graph
                  </h2>
                  <p className="text-[9px] text-muted mt-0.5">Statistical confidence scores plotted sequentially</p>
                </div>
                <span className="text-[9px] font-mono text-slate-300 bg-white/5 px-2 py-0.5 rounded border border-white/5">
                  {chartData.length} pts
                </span>
              </div>

              <div className="flex-grow p-4 flex flex-col justify-center min-h-0 relative bg-slate-950/10">
                {chartData.length === 0 ? (
                  <div className="flex flex-col items-center justify-center text-muted/65 text-center p-4">
                    <Activity className="w-12 h-12 mb-2 animate-pulse text-muted/30" />
                    <p className="text-xs font-semibold tracking-wider font-mono uppercase">No Telemetry Data Available</p>
                    <p className="text-[10px] text-muted/50 mt-1 font-mono">Inference points construct graph dynamically</p>
                  </div>
                ) : (
                  <div className="w-full h-full min-h-[200px] relative">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 20, right: 10, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.02)" vertical={false} />
                        <XAxis dataKey="time" stroke="#64748b" fontSize={9} tickMargin={8} />
                        <YAxis stroke="#64748b" fontSize={9} domain={[0, 100]} />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: 'rgba(19, 27, 46, 0.95)', 
                            borderColor: 'rgba(255, 255, 255, 0.1)', 
                            borderRadius: '12px',
                            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.5)',
                            fontSize: '11px',
                            fontFamily: 'Outfit, sans-serif'
                          }}
                          itemStyle={{ color: '#6366f1' }}
                        />
                        {/* Glow filter underlay */}
                        <Line 
                          type="monotone" 
                          dataKey="confidence" 
                          stroke="#6366f1" 
                          strokeWidth={8}
                          opacity={0.15}
                          dot={false}
                          activeDot={false}
                        />
                        {/* Crisp front line */}
                        <Line 
                          type="monotone" 
                          dataKey="confidence" 
                          stroke="url(#chartGradPrimaryTab2)" 
                          strokeWidth={3.5}
                          dot={{ r: 4, fill: '#6366f1', strokeWidth: 1.5, stroke: '#ffffff' }}
                          activeDot={{ r: 6, fill: '#f43f5e', stroke: '#ffffff', strokeWidth: 1.5 }}
                        />
                        <defs>
                          <linearGradient id="chartGradPrimaryTab2" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor="#6366f1" />
                            <stop offset="50%" stopColor="#818cf8" />
                            <stop offset="100%" stopColor="#f43f5e" />
                          </linearGradient>
                        </defs>
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>

            {/* Center Column: Detection Map (Map rendered in Tab 2 as well!) */}
            <div className="lg:col-span-4 glass-panel rounded-2xl overflow-hidden relative lg:h-full h-[400px] min-h-[300px]">
              <div className="absolute top-4 right-4 z-[1000] bg-slate-950/85 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-white/5 shadow-2xl flex items-center gap-2">
                 <MapPin className="w-3.5 h-3.5 text-accent animate-bounce" />
                 <h2 className="font-extrabold text-slate-100 text-xs tracking-wider uppercase font-mono">Detection Map</h2>
              </div>
              
              <MapContainer 
                center={mapCenter} 
                zoom={mapZoom} 
                style={{ height: '100%', width: '100%', position: 'absolute', top: 0, left: 0 }}
                className="z-0"
              >
                <ChangeMapView center={mapCenter} zoom={mapZoom} />
                <TileLayer
                  attribution='&copy; OpenStreetMap'
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />
                {detections.map((det) => (
                  <Marker 
                    key={det.id} 
                    position={[det.latitude, det.longitude]}
                    icon={createGlowingMarker(det.confidence)}
                  >
                    <Popup className="custom-popup">
                      <div className="w-48 flex flex-col gap-2 p-1.5 text-text">
                        <div className="relative rounded-lg overflow-hidden border border-white/5 shadow-inner bg-black/40 h-28">
                          <img 
                            src={`${API_BASE_URL}${det.image_path}`} 
                            alt="Pothole detection" 
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="bg-slate-950/60 rounded-lg p-2 border border-white/5 text-[10px] space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="text-muted">Confidence</span>
                            <span className="font-bold text-accent font-mono text-xs">
                              {(det.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-muted">Coords</span>
                            <span className="font-mono text-[9px]">
                              {det.latitude.toFixed(4)}, {det.longitude.toFixed(4)}
                            </span>
                          </div>
                          <div className="pt-1 mt-1 border-t border-white/5 text-[8px] text-muted font-mono">
                            {new Date(det.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>

            {/* Right Column: Analytical Summary Cards */}
            <div className="lg:col-span-3 glass-panel rounded-2xl flex flex-col lg:h-full h-auto overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-slate-950/45 flex items-center justify-between">
                <h2 className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-2">
                  <Award className="w-3.5 h-3.5 text-accent" /> Telemetry Insights
                </h2>
                <span className="text-[8px] font-mono tracking-widest text-primary uppercase">ANALYTICS_V1</span>
              </div>

              {/* Enhanced Scrollable list container with shadows */}
              <div className="flex-grow relative min-h-0 bg-slate-950/10">
                <div className="absolute top-0 left-0 right-0 h-4 bg-gradient-to-b from-[#090d16]/30 to-transparent pointer-events-none z-10" />
                <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[#090d16]/50 to-transparent pointer-events-none z-10" />

                <div className="w-full h-full overflow-y-auto p-4 space-y-4 custom-scrollbar pr-2">
                  {/* Average Confidence */}
                  <div className="bg-slate-950/40 rounded-xl p-3 border border-white/5 flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="text-[9px] text-muted uppercase tracking-widest font-bold">Running Avg Confidence</p>
                      <p className="text-lg font-extrabold text-primary font-mono">{runningAvgConf}%</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-primary" />
                    </div>
                  </div>

                  {/* Peak Confidence */}
                  <div className="bg-slate-950/40 rounded-xl p-3 border border-white/5 flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="text-[9px] text-muted uppercase tracking-widest font-bold">Peak Severity Score</p>
                      <p className="text-lg font-extrabold text-accent font-mono">{peakConf}%</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
                      <Zap className="w-5 h-5 text-accent animate-pulse" />
                    </div>
                  </div>

                  {/* Severity Breakdown Bar */}
                  <div className="bg-slate-950/40 rounded-xl p-4 border border-white/5 space-y-2.5">
                    <p className="text-[9px] text-muted uppercase tracking-widest font-bold">Risk Breakdown</p>
                    <div className="flex items-center justify-between text-[10px] font-mono">
                      <span className="flex items-center gap-1.5 text-red-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> High Risk ({highRiskCount})
                      </span>
                      <span className="flex items-center gap-1.5 text-amber-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Medium Risk ({medRiskCount})
                      </span>
                    </div>
                    {/* Progress Ratio Bar */}
                    <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden flex border border-white/5">
                      <div 
                        className="bg-red-500 h-full transition-all duration-500" 
                        style={{ width: `${detections.length > 0 ? highRiskPct : 0}%` }}
                      />
                      <div 
                        className="bg-amber-500 h-full transition-all duration-500" 
                        style={{ width: `${detections.length > 0 ? medRiskPct : 0}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[8px] text-muted font-mono tracking-wide pt-1">
                      <span>HIGH: {highRiskPct}%</span>
                      <span>MED: {medRiskPct}%</span>
                    </div>
                  </div>

                  {/* Edge Systems Diagnostics */}
                  <div className="bg-slate-950/40 rounded-xl p-4 border border-white/5 space-y-3">
                    <p className="text-[9px] text-muted uppercase tracking-widest font-bold flex items-center gap-1.5">
                      <Compass className="w-3.5 h-3.5 text-indigo-400" /> System Diagnostics
                    </p>
                    <div className="space-y-2 text-[10px] font-mono">
                      <div className="flex justify-between items-center py-1 border-b border-white/5">
                        <span className="text-muted">Edge Temp</span>
                        <span className="text-slate-200">46.5 °C</span>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-white/5">
                        <span className="text-muted">VRAM Allocation</span>
                        <span className="text-slate-200">1.84 GB / 8.00 GB</span>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-white/5">
                        <span className="text-muted">Inference Delay</span>
                        <span className="text-emerald-400">38.4 ms</span>
                      </div>
                      <div className="flex justify-between items-center py-1">
                        <span className="text-muted">Uptime (Session)</span>
                        <span className="text-slate-200">00h 14m 22s</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}

export default App;
