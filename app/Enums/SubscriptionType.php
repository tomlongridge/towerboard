<?php

namespace App\Enums;

use BenSampo\Enum\Enum;

final class SubscriptionType extends Enum
{
    const BASIC  = 00;
    const MEMBER = 10;
    const ADMIN  = 20;

    public static function getDescription($value): string
    {
        if ($value === self::BASIC) {
            return 'Subscriber';
        } elseif ($value === self::MEMBER) {
            return 'Member';
        } elseif ($value === self::ADMIN) {
            return 'Administrator';
        }

        return parent::getDescription($value);
    }
}
