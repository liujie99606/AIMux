import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import './styles/index.scss';
import router from './router';
import App from './App.vue';

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app');
