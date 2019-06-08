<?php

use Illuminate\Database\Seeder;
use App\Enums\SubscriptionType;

class UsersTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        DB::table('users')->insert([
            'forename' => 'Tom',
            'middle_initials' => '',
            'surname' => 'Longridge',
            'email' => 'tomlongridge@gmail.com',
            'password' => bcrypt('p'),
            'email_verified_at' => new DateTime,
        ]);

        DB::table('users')->insert([
            'forename' => 'Sue',
            'middle_initials' => '',
            'surname' => 'Member',
            'email' => 'tomlongridge+sue@gmail.com',
            'password' => bcrypt('p'),
            'email_verified_at' => new DateTime,
        ]);

        DB::table('users')->insert([
            'forename' => 'Ann',
            'middle_initials' => '',
            'surname' => 'Other',
            'email' => 'tomlongridge+ann@gmail.com',
            'password' => bcrypt('p'),
            'email_verified_at' => new DateTime,
        ]);
    }
}
