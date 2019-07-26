<?php

namespace App\Notifications;

use App\User;

use Illuminate\Bus\Queueable;
use Illuminate\Notifications\Notification;
use Illuminate\Contracts\Queue\ShouldQueue;
use App\Board;

class BoardCreated extends Notification implements ShouldQueue
{
    use Queueable;

    private $board;

    /**
     * Create a new notification instance.
     *
     * @return void
     */
    public function __construct(Board $board)
    {
        $this->board = $board;
    }

    /**
     * Get the notification's delivery channels.
     *
     * @param  mixed  $notifiable
     * @return array
     */
    public function via(User $user)
    {
        return ['mail'];
    }

    /**
     * Get the mail representation of the notification.
     *
     * @param  mixed  $notifiable
     * @return \Illuminate\Notifications\Messages\MailMessage
     */
    public function toMail(User $user)
    {
        return (new \App\Mail\BoardCreated($this->board))->to($user->email);
    }

    /**
     * Get the array representation of the notification.
     *
     * @param  mixed  $notifiable
     * @return array
     */
    public function toArray(User $user)
    {
        return [
            //
        ];
    }
}
