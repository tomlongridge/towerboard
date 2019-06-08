<?php

namespace App\Policies;

use App\User;
use App\Board;
use Illuminate\Auth\Access\HandlesAuthorization;

class SubscriptionPolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can create board subscriptions.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function create(?User $user, Board $board, User $subscriber)
    {
        if ($subscriber->id == null) {
            return false;
        } elseif ($subscriber->id == $user->id) {
            return true;
        } else {
            return $board->owner->id == $user->id;
        }
    }

    /**
     * Determine whether the user can update board subscriptions.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function update(?User $user, Board $board, User $subscriber)
    {
        if ($subscriber->id == null) {
            return false;
        } elseif ($subscriber->id == $user->id) {
            return true;
        } else {
            return $board->owner->id == $user->id;
        }
    }

    public function addUser(?User $user, Board $board)
    {
        return $board->owner->id == $user->id;
    }

    /**
     * Determine whether the user can delete the board subscription.
     *
     * @param  \App\User  $user
     * @param  \App\BoardSubscription  $boardSubscription
     * @return mixed
     */
    public function delete(User $user, Board $board, User $subscriber)
    {
        if ($subscriber->id == null) {
            return false;
        } elseif ($subscriber->id == $user->id) {
            return true;
        } else {
            return $board->owner->id == $user->id;
        }
    }
}
