/**
 * Simple date formatting utility.
 * 
 * Formats a date string as relative time (e.g., "5 minutes ago").
 * Uses built-in Intl.RelativeTimeFormat when available.
 */

const MINUTE = 60;
const HOUR = MINUTE * 60;
const DAY = HOUR * 24;
const WEEK = DAY * 7;
const MONTH = DAY * 30;
const YEAR = DAY * 365;

/**
 * Format a date as relative time from now.
 * 
 * @param {string|Date} date - The date to format
 * @returns {string} Relative time string (e.g., "5 minutes ago")
 */
export function formatDistanceToNow(date) {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffInSeconds = Math.floor((now - dateObj) / 1000);

  if (diffInSeconds < 30) {
    return 'just now';
  }

  if (diffInSeconds < MINUTE) {
    return `${diffInSeconds} seconds ago`;
  }

  if (diffInSeconds < HOUR) {
    const minutes = Math.floor(diffInSeconds / MINUTE);
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
  }

  if (diffInSeconds < DAY) {
    const hours = Math.floor(diffInSeconds / HOUR);
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
  }

  if (diffInSeconds < WEEK) {
    const days = Math.floor(diffInSeconds / DAY);
    return `${days} ${days === 1 ? 'day' : 'days'} ago`;
  }

  if (diffInSeconds < MONTH) {
    const weeks = Math.floor(diffInSeconds / WEEK);
    return `${weeks} ${weeks === 1 ? 'week' : 'weeks'} ago`;
  }

  if (diffInSeconds < YEAR) {
    const months = Math.floor(diffInSeconds / MONTH);
    return `${months} ${months === 1 ? 'month' : 'months'} ago`;
  }

  const years = Math.floor(diffInSeconds / YEAR);
  return `${years} ${years === 1 ? 'year' : 'years'} ago`;
}
