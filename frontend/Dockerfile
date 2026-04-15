FROM node:18-alpine

WORKDIR /app

# Копируем зависимости отдельно для кэширования слоев
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходный код (для production сборки)
# В development режиме код монтируется через volume,
# поэтому это нужно для первичной сборки образа
COPY . .

EXPOSE 3000

# Запускаем dev-сервер React (CRA)
CMD ["npm", "start"]