import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp up to 5 users
    { duration: '1m', target: 20 },   // Ramp up to 20 users
    { duration: '30s', target: 50 },  // Spike to 50 users
    { duration: '1m', target: 50 },   // Stay at 50
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    errors: ['rate<0.1'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const complaints = [
  { text: 'Burst water main flooding Street 12 since fajr, water entering ground floors of houses nearby', location: 'Street 12, Gulberg III, Lahore' },
  { text: 'Bijli ka transformer phat gaya raat ko, poora mohalla andhera mein hai since 2am today', location: 'Gulshan-e-Iqbal Block 6, Karachi' },
  { text: 'Garbage not collected for three days now, kachra everywhere on the streets and in drain', location: 'Johar Town Block D, Lahore' },
  { text: 'Bohut bara pothole hai main road pe, raat ko ek motorcycle wala gir gaya last night', location: 'Multan Road near Thokar Niaz Baig' },
  { text: 'Street light band hai pichle ek hafte se gali mein, raat ko bilkul andhera rehta hai', location: 'Street 4, Westridge, Rawalpindi' },
];

export default function () {
  // Mix of read and write operations
  const rand = Math.random();

  if (rand < 0.3) {
    // 30% — Submit a complaint
    const complaint = complaints[Math.floor(Math.random() * complaints.length)];
    const res = http.post(`${BASE_URL}/api/complaints`, JSON.stringify(complaint), {
      headers: { 'Content-Type': 'application/json' },
    });
    check(res, { 'POST status is 201 or 429': (r) => r.status === 201 || r.status === 429 });
    errorRate.add(res.status !== 201 && res.status !== 429);
  } else if (rand < 0.6) {
    // 30% — List complaints
    const res = http.get(`${BASE_URL}/api/complaints?page=1&page_size=10`);
    check(res, { 'GET list status is 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  } else if (rand < 0.8) {
    // 20% — Get stats
    const res = http.get(`${BASE_URL}/api/stats`);
    check(res, { 'GET stats is 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  } else {
    // 20% — Health check
    const res = http.get(`${BASE_URL}/health`);
    check(res, { 'health is 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  }

  sleep(0.5 + Math.random());
}
